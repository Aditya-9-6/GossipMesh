import logging

from sqlalchemy.orm import Session

from gossipmesh.models.runtime import Job, Workflow

logger = logging.getLogger(__name__)

class WorkflowManager:
    def __init__(self, db: Session):
        self.db = db

    def create_workflow(self, organization_id: int, repository_id: int) -> Workflow:
        workflow = Workflow(
            organization_id=organization_id,
            repository_id=repository_id,
            status="pending"
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def add_job(self, workflow_id: int, agent_name: str) -> Job:
        job = Job(
            workflow_id=workflow_id,
            agent_name=agent_name,
            status="pending"
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job_status(self, job_id: int, status: str, state: dict = None):
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            if state:
                job.state = state
            self.db.commit()
            self._evaluate_workflow_state(job.workflow_id)

    def _evaluate_workflow_state(self, workflow_id: int):
        """State machine logic to update overall workflow status based on jobs."""
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            return

        jobs = self.db.query(Job).filter(Job.workflow_id == workflow_id).all()
        statuses = [j.status for j in jobs]

        if "failed" in statuses:
            workflow.status = "failed"
        elif "blocked" in statuses:
             workflow.status = "blocked" # Awaiting human approval
        elif all(s == "completed" for s in statuses):
            workflow.status = "completed"
        elif "running" in statuses:
            workflow.status = "running"

        self.db.commit()

    def cancel_workflow(self, workflow_id: int):
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow and workflow.status not in ("completed", "failed"):
            workflow.status = "cancelled"
            jobs = self.db.query(Job).filter(Job.workflow_id == workflow_id).all()
            for job in jobs:
                if job.status not in ("completed", "failed"):
                    job.status = "cancelled"
            self.db.commit()

    def approve_patch(self, workflow_id: int):
        """Unblocks a workflow that requires human patch approval."""
        workflow = self.db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow and workflow.status == "blocked":
            workflow.status = "running"
            self.db.commit()
            # In a real system, this would enqueue the next step of the workflow via Celery
