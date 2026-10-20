from sqlalchemy.orm import Session
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.models.audit import AuditEvent
from gossipmesh.runtime.budget import BudgetManager
import logging

logger = logging.getLogger(__name__)


class WorkflowManager:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(self, organization_id: int, repository_id: int, actor_id: int | None = None) -> Workflow:
        try:
            workflow = Workflow(organization_id=organization_id, repository_id=repository_id, status="pending")
            self.db.add(workflow)
            self.db.flush()

            audit = AuditEvent(
                action="workflow_created",
                actor_id=actor_id,
                organization_id=organization_id,
                details={"workflow_id": workflow.id},
            )
            self.db.add(audit)

            self.db.commit()
            self.db.refresh(workflow)
            return workflow
        except Exception:
            self.db.rollback()
            raise

    def add_job(self, workflow_id: int, agent_name: str, actor_id: int | None = None) -> Job:
        try:
            job = Job(workflow_id=workflow_id, agent_name=agent_name, status="pending")
            self.db.add(job)
            self.db.flush()

            workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow:
                audit = AuditEvent(
                    action="job_added",
                    actor_id=actor_id,
                    organization_id=workflow.organization_id,
                    details={"job_id": job.id, "workflow_id": workflow_id},
                )
                self.db.add(audit)

            self.db.commit()
            self.db.refresh(job)
            return job
        except Exception:
            self.db.rollback()
            raise

    def create_workflow_with_job(
        self, organization_id: int, repository_id: int, agent_name: str, actor_id: int | None = None
    ) -> tuple[Workflow, Job]:
        try:
            workflow = Workflow(organization_id=organization_id, repository_id=repository_id, status="pending")
            self.db.add(workflow)
            self.db.flush()

            job = Job(workflow_id=workflow.id, agent_name=agent_name, status="pending")
            self.db.add(job)
            self.db.flush()

            audit_wf = AuditEvent(
                action="workflow_created",
                actor_id=actor_id,
                organization_id=organization_id,
                details={"workflow_id": workflow.id},
            )
            self.db.add(audit_wf)

            audit_job = AuditEvent(
                action="job_added",
                actor_id=actor_id,
                organization_id=organization_id,
                details={"job_id": job.id, "workflow_id": workflow.id},
            )
            self.db.add(audit_job)

            self.db.commit()
            self.db.refresh(workflow)
            self.db.refresh(job)
            return workflow, job
        except Exception:
            self.db.rollback()
            raise

    def update_job_status(self, job_id: int, status: str, state: dict | None = None, actor_id: int | None = None):
        try:
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = status
                if state:
                    job.state = state
                self.db.flush()

                workflow = self.db.query(Workflow).filter(Workflow.id == job.workflow_id).first()
                if workflow:
                    audit = AuditEvent(
                        action="job_status_updated",
                        actor_id=actor_id,
                        organization_id=workflow.organization_id,
                        details={"job_id": job.id, "status": status},
                    )
                    self.db.add(audit)

                self._evaluate_workflow_state_no_commit(job.workflow_id)
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _evaluate_workflow_state(self, workflow_id: int):
        try:
            self._evaluate_workflow_state_no_commit(workflow_id)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _evaluate_workflow_state_no_commit(self, workflow_id: int):
        """State machine logic to update overall workflow status based on jobs."""
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            return

        jobs = self.db.query(Job).filter(Job.workflow_id == workflow_id).all()
        statuses = [j.status for j in jobs]

        if "failed" in statuses:
            workflow.status = "failed"
        elif "blocked" in statuses:
            workflow.status = "blocked"  # Awaiting human approval
        elif all(s == "completed" for s in statuses):
            workflow.status = "completed"
        elif "running" in statuses:
            workflow.status = "running"

        self.db.flush()

    def check_cancellation(self, workflow_id: int) -> bool:
        """
        Checks if the workflow is cancelled or has exceeded its deadline.
        Returns True if cancelled or timed out, False otherwise.
        """
        try:
            workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not workflow:
                return False

            if workflow.status == "cancelled":
                return True

            if workflow.deadline:
                from datetime import datetime, timezone

                # SQLite returns naive datetimes even for Timestamp(timezone=True)
                db_deadline = workflow.deadline
                if db_deadline.tzinfo is None:
                    db_deadline = db_deadline.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > db_deadline:
                    workflow.status = "failed"
                    jobs = self.db.query(Job).filter(Job.workflow_id == workflow_id).all()
                    for job in jobs:
                        if job.status not in ("completed", "failed"):
                            job.status = "cancelled"
                            if not job.state:
                                job.state = {}
                            job.state["error"] = "deadline_exceeded"
                    self.db.flush()

                    audit = AuditEvent(
                        action="workflow_timeout",
                        actor_id=None,
                        organization_id=workflow.organization_id,
                        details={"workflow_id": workflow.id},
                    )
                    self.db.add(audit)
                    self.db.commit()
                    return True

            return False
        except Exception:
            self.db.rollback()
            raise

    def cancel_workflow(self, workflow_id: int, actor_id: int | None = None):
        try:
            workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow and workflow.status not in ("completed", "failed"):
                workflow.status = "cancelled"
                jobs = self.db.query(Job).filter(Job.workflow_id == workflow_id).all()
                for job in jobs:
                    if job.status not in ("completed", "failed"):
                        job.status = "cancelled"
                self.db.flush()

                audit = AuditEvent(
                    action="workflow_cancelled",
                    actor_id=actor_id,
                    organization_id=workflow.organization_id,
                    details={"workflow_id": workflow.id},
                )
                self.db.add(audit)
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def approve_patch(self, workflow_id: int, actor_id: int | None = None):
        """Unblocks a workflow that requires human patch approval."""
        try:
            workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow and workflow.status == "blocked":
                workflow.status = "running"
                self.db.flush()

                BudgetManager(self.db).record_spend(workflow.organization_id, 1.0, commit=False)

                audit = AuditEvent(
                    action="workflow_approved",
                    actor_id=actor_id,
                    organization_id=workflow.organization_id,
                    details={"workflow_id": workflow.id},
                )
                self.db.add(audit)

                self.db.commit()
                # In a real system, this would enqueue the next step of the workflow via Celery
        except Exception:
            self.db.rollback()
            raise
