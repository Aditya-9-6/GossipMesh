"""Workflow Scheduler, Priority Queue, Customer Plan Limits, and Graceful Shutdown (Task 64).

Handles:
- Priority-based scheduling (Emergency/Security > Normal Review > Scheduled Indexing)
- Customer plan limits and priority boosts (Enterprise > Pro > Free)
- Scheduled repository indexing and queued pull request reviews
- Graceful shutdown with in-flight worker draining
"""

import time
import threading
import logging
from enum import IntEnum
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from gossipmesh.core.exceptions import ConflictError, RateLimitError
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.models.repository import Repository, IndexState, RepositoryPolicy
from gossipmesh.models.audit import AuditEvent
from gossipmesh.runtime.worker_lease import WorkerLeaseManager

logger = logging.getLogger(__name__)


class JobPriority(IntEnum):
    LOW = 10  # Background maintenance, scheduled indexing
    NORMAL = 50  # Standard PR reviews, CI webhook triggers
    CRITICAL = 100  # Security hotfixes, manual user-requested reviews


PLAN_PRIORITY_BOOSTS: Dict[str, int] = {
    "free": 0,
    "pro": 15,
    "enterprise": 30,
}

PLAN_QUEUE_LIMITS: Dict[str, int] = {
    "free": 5,
    "pro": 25,
    "enterprise": 100,
}


class GracefulShutdownController:
    """Coordinates graceful shutdown across background schedulers and workers."""

    def __init__(self):
        self._shutting_down = threading.Event()
        self._active_jobs_count = 0
        self._lock = threading.Lock()

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down.is_set()

    def initiate_shutdown(self) -> None:
        """Signals that the system is entering shutdown; new jobs will be rejected."""
        self._shutting_down.set()
        logger.info("Graceful shutdown initiated. Draining in-flight jobs...")

    def register_job_start(self) -> None:
        if self.is_shutting_down:
            raise RuntimeError("Scheduler is shutting down. New jobs cannot be accepted.")
        with self._lock:
            self._active_jobs_count += 1

    def register_job_finish(self) -> None:
        with self._lock:
            self._active_jobs_count = max(0, self._active_jobs_count - 1)

    def wait_for_drain(self, timeout_seconds: float = 30.0) -> bool:
        """Blocks until active jobs reach zero or timeout expires."""
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            with self._lock:
                if self._active_jobs_count == 0:
                    return True
            time.sleep(0.2)
        return False

    def reset(self) -> None:
        with self._lock:
            self._shutting_down.clear()
            self._active_jobs_count = 0


shutdown_controller = GracefulShutdownController()


class WorkflowScheduler:
    """Enterprise job scheduler with priority queues, plan limits, and scheduled tasks."""

    @staticmethod
    def calculate_effective_priority(
        base_priority: JobPriority,
        plan_tier: str = "free",
    ) -> int:
        """Calculates total priority including customer plan tier boost."""
        boost = PLAN_PRIORITY_BOOSTS.get(plan_tier.lower(), 0)
        return int(base_priority) + boost

    @classmethod
    def check_plan_queue_capacity(
        cls,
        db: Session,
        organization_id: int,
        plan_tier: str = "free",
    ) -> None:
        """Enforces customer plan limits on maximum queued pending jobs."""
        queue_limit = PLAN_QUEUE_LIMITS.get(plan_tier.lower(), 5)
        pending_count = (
            db.query(Job)
            .join(Workflow, Job.workflow_id == Workflow.id)
            .filter(Workflow.organization_id == organization_id, Job.status == "pending")
            .count()
        )
        if pending_count >= queue_limit:
            raise RateLimitError(
                message=(
                    f"Customer plan queue limit reached for organization {organization_id}: "
                    f"{pending_count}/{queue_limit} pending jobs queued under '{plan_tier}' tier."
                )
            )

    @classmethod
    def enqueue_review(
        cls,
        db: Session,
        repository_id: int,
        organization_id: int,
        pr_number: int,
        is_user_triggered: bool = False,
        plan_tier: str = "free",
        actor_id: Optional[int] = None,
    ) -> Tuple[Workflow, Job]:
        """Enqueues a pull request review with priority and plan capacity enforcement."""
        if shutdown_controller.is_shutting_down:
            raise RuntimeError("Scheduler is shutting down. Rejecting new review jobs.")

        cls.check_plan_queue_capacity(db, organization_id, plan_tier)

        base_prio = JobPriority.CRITICAL if is_user_triggered else JobPriority.NORMAL
        effective_prio = cls.calculate_effective_priority(base_prio, plan_tier)

        workflow = Workflow(organization_id=organization_id, repository_id=repository_id, status="pending")
        db.add(workflow)
        db.flush()

        job = Job(
            workflow_id=workflow.id,
            agent_name="ai_pr_reviewer",
            status="pending",
            state={
                "pr_number": pr_number,
                "priority": effective_prio,
                "base_priority": int(base_prio),
                "plan_tier": plan_tier,
                "is_user_triggered": is_user_triggered,
            },
        )
        db.add(job)

        audit = AuditEvent(
            action="workflow.review_enqueued",
            actor_id=actor_id,
            organization_id=organization_id,
            details={
                "workflow_id": workflow.id,
                "job_id": job.id,
                "pr_number": pr_number,
                "effective_priority": effective_prio,
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(workflow)
        db.refresh(job)
        return workflow, job

    @classmethod
    def schedule_indexing(
        cls,
        db: Session,
        repository_id: int,
        organization_id: int,
        plan_tier: str = "free",
        force: bool = False,
    ) -> Optional[Tuple[Workflow, Job]]:
        """Schedules repository background indexing if due per policy or forced."""
        if shutdown_controller.is_shutting_down:
            raise RuntimeError("Scheduler is shutting down. Rejecting indexing jobs.")

        # Check existing pending/running indexing job
        existing_active = (
            db.query(Job)
            .join(Workflow, Job.workflow_id == Workflow.id)
            .filter(
                Workflow.repository_id == repository_id,
                Job.agent_name == "repository_indexer",
                Job.status.in_(["pending", "running"]),
            )
            .first()
        )
        if existing_active:
            return None

        # Check policy scan frequency
        idx_state = db.query(IndexState).filter(IndexState.repository_id == repository_id).first()
        if not force and idx_state and idx_state.last_indexed_at:
            policy = db.query(RepositoryPolicy).filter(RepositoryPolicy.repository_id == repository_id).first()
            freq_hours = policy.scan_frequency_hours if policy else 24
            cutoff = datetime.now(timezone.utc) - timedelta(hours=freq_hours)
            last_indexed = idx_state.last_indexed_at
            if last_indexed.tzinfo is None:
                last_indexed = last_indexed.replace(tzinfo=timezone.utc)
            if last_indexed > cutoff:
                return None  # Not due yet

        effective_prio = cls.calculate_effective_priority(JobPriority.LOW, plan_tier)

        workflow = Workflow(organization_id=organization_id, repository_id=repository_id, status="pending")
        db.add(workflow)
        db.flush()

        job = Job(
            workflow_id=workflow.id,
            agent_name="repository_indexer",
            status="pending",
            state={
                "priority": effective_prio,
                "base_priority": int(JobPriority.LOW),
                "plan_tier": plan_tier,
                "forced": force,
            },
        )
        db.add(job)

        audit = AuditEvent(
            action="workflow.indexing_scheduled",
            actor_id=None,
            organization_id=organization_id,
            details={
                "workflow_id": workflow.id,
                "job_id": job.id,
                "repository_id": repository_id,
                "priority": effective_prio,
            },
        )
        db.add(audit)
        db.commit()
        db.refresh(workflow)
        db.refresh(job)
        return workflow, job

    @classmethod
    def dispatch_next_job(
        cls,
        db: Session,
        worker_id: str,
        lease_duration_seconds: int = 60,
    ) -> Tuple[Optional[Job], Optional[str]]:
        """Finds the highest priority pending job and claims it for the worker."""
        if shutdown_controller.is_shutting_down:
            return None, None

        # Fetch pending jobs
        pending_jobs = db.query(Job).filter(Job.status == "pending").order_by(Job.created_at.asc()).all()
        if not pending_jobs:
            return None, None

        # Sort by effective priority descending, then creation time ascending
        def get_prio(j: Job) -> int:
            if j.state and isinstance(j.state, dict):
                return j.state.get("priority", int(JobPriority.NORMAL))
            return int(JobPriority.NORMAL)

        sorted_jobs = sorted(pending_jobs, key=lambda j: (-get_prio(j), j.id))

        # Attempt to acquire lease on highest priority job
        for candidate in sorted_jobs:
            job, lease_token = WorkerLeaseManager.acquire_job_lease(
                db=db,
                worker_id=worker_id,
                job_id=candidate.id,
                lease_duration_seconds=lease_duration_seconds,
            )
            if job and lease_token:
                shutdown_controller.register_job_start()
                return job, lease_token

        return None, None
