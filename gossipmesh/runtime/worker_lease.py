"""Worker identity, lease ownership, heartbeat renewal, and crash recovery (Task 63).

Enforces worker ownership, lease expiry timeouts, crash recovery, and
fencing tokens to prevent duplicate execution across distributed workers.
"""

import os
import socket
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from gossipmesh.core.exceptions import ConflictError
from gossipmesh.models.runtime import Job
from gossipmesh.models.audit import AuditEvent

logger = logging.getLogger(__name__)


class WorkerLeaseManager:
    """Manages worker job leases, fencing tokens, heartbeats, and abandoned job recovery."""

    @staticmethod
    def generate_worker_id(prefix: str = "worker") -> str:
        """Generates a globally unique identifier for a worker process."""
        hostname = socket.gethostname().split(".")[0]
        pid = os.getpid()
        random_suffix = uuid.uuid4().hex[:8]
        return f"{prefix}-{hostname}-{pid}-{random_suffix}"

    @classmethod
    def acquire_job_lease(
        cls,
        db: Session,
        worker_id: str,
        job_id: Optional[int] = None,
        lease_duration_seconds: int = 60,
        max_retries: int = 3,
    ) -> Tuple[Optional[Job], Optional[str]]:
        """Atomically acquires an exclusive lease on a job.

        If job_id is provided, attempts to acquire that specific job.
        Otherwise, finds the oldest pending or abandoned job.

        Returns:
            (job, lease_token) if acquired, or (None, None) if no job available.
        """
        now = datetime.now(timezone.utc)

        query = db.query(Job)
        if job_id is not None:
            query = query.filter(Job.id == job_id)

        # Eligible if pending, OR if running but lease has expired and attempts < max_retries
        eligible_filter = or_(
            Job.status == "pending",
            and_(
                Job.status == "running",
                Job.lease_expires_at != None,
                Job.lease_expires_at < now,
                Job.attempts < max_retries,
            ),
        )
        job = query.filter(eligible_filter).order_by(Job.id.asc()).with_for_update().first()

        if not job:
            return None, None

        lease_token = str(uuid.uuid4())
        job.status = "running"
        job.worker_id = worker_id
        job.lease_token = lease_token
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
        job.attempts = (job.attempts or 0) + 1

        db.commit()
        db.refresh(job)
        return job, lease_token

    @classmethod
    def heartbeat(
        cls,
        db: Session,
        job_id: int,
        worker_id: str,
        lease_token: str,
        extend_seconds: int = 60,
    ) -> bool:
        """Sends a heartbeat to extend the job's lease.

        Validates the fencing token to ensure the lease was not revoked or stolen.
        Raises ConflictError if the lease token no longer matches.
        """
        now = datetime.now(timezone.utc)
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ConflictError(message=f"Job {job_id} does not exist.")

        # Fencing check
        if job.worker_id != worker_id or job.lease_token != lease_token:
            raise ConflictError(
                message=(
                    f"Fencing violation: Worker '{worker_id}' lease on Job {job_id} "
                    f"has expired or was acquired by another worker."
                )
            )

        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=extend_seconds)
        db.commit()
        return True

    @classmethod
    def complete_job(
        cls,
        db: Session,
        job_id: int,
        worker_id: str,
        lease_token: str,
        result_state: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Marks a job as completed, validating the lease fencing token to prevent duplicate execution."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ConflictError(message=f"Job {job_id} not found.")

        # Duplicate execution / stolen lease fencing check
        if job.worker_id != worker_id or job.lease_token != lease_token:
            raise ConflictError(
                message=(
                    f"Duplicate execution prevented: Worker '{worker_id}' cannot complete Job {job_id} "
                    f"because its lease has expired or been reassigned."
                )
            )

        job.status = "completed"
        if result_state is not None:
            job.state = result_state
        job.lease_token = None
        job.lease_expires_at = None

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def fail_job(
        cls,
        db: Session,
        job_id: int,
        worker_id: str,
        lease_token: str,
        error_message: str,
    ) -> Job:
        """Marks a job as failed, validating the lease fencing token."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ConflictError(message=f"Job {job_id} not found.")

        if job.worker_id != worker_id or job.lease_token != lease_token:
            raise ConflictError(message=f"Worker '{worker_id}' lease on Job {job_id} is no longer valid.")

        job.status = "failed"
        job.state = {"error": error_message}
        job.lease_token = None
        job.lease_expires_at = None

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def recover_abandoned_jobs(
        cls,
        db: Session,
        max_retries: int = 3,
    ) -> Dict[str, List[int]]:
        """Sweeps running jobs whose leases have expired (e.g. worker node crashed)
        and resets them for retry or marks them failed if max attempts exceeded.
        """
        now = datetime.now(timezone.utc)
        orphaned = (
            db.query(Job)
            .filter(
                Job.status == "running",
                Job.lease_expires_at != None,
                Job.lease_expires_at < now,
            )
            .all()
        )

        recovered = []
        exhausted = []

        for job in orphaned:
            if (job.attempts or 0) < max_retries:
                # Reset to pending for retry
                job.status = "pending"
                prev_worker = job.worker_id
                job.worker_id = None
                job.lease_token = None
                job.lease_expires_at = None

                audit = AuditEvent(
                    action="job.recovered_from_crash",
                    actor_id=None,
                    organization_id=None,
                    details={
                        "job_id": job.id,
                        "workflow_id": job.workflow_id,
                        "previous_worker": prev_worker,
                        "attempt": job.attempts,
                    },
                )
                db.add(audit)
                recovered.append(job.id)
            else:
                job.status = "failed"
                job.state = {"error": "Maximum crash recovery retries exceeded"}
                job.lease_token = None
                job.lease_expires_at = None

                audit = AuditEvent(
                    action="job.permanently_failed",
                    actor_id=None,
                    organization_id=None,
                    details={"job_id": job.id, "attempts": job.attempts},
                )
                db.add(audit)
                exhausted.append(job.id)

        db.commit()
        return {"recovered": recovered, "exhausted": exhausted}
