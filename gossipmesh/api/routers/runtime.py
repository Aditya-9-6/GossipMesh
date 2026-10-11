from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.runtime.workflow import WorkflowManager

router = APIRouter()

class CreateWorkflowRequest(BaseModel):
    organization_id: int
    repository_id: int
    agent_name: str

@router.post("/workflows", status_code=201)
def create_workflow(
    request: CreateWorkflowRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    # Ensure user has access to organization
    user_org_ids = [org.organization_id for org in current_user.organizations]
    if request.organization_id not in user_org_ids:
        raise HTTPException(status_code=403, detail="Not authorized for this organization")

    manager = WorkflowManager(db)
    workflow = manager.create_workflow(request.organization_id, request.repository_id)
    job = manager.add_job(workflow.id, request.agent_name)

    # Normally this would enqueue a Celery task to begin execution
    return {"workflow_id": workflow.id, "job_id": job.id, "status": workflow.status}

@router.post("/workflows/{workflow_id}/cancel")
def cancel_workflow(
    workflow_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    # Proper auth check on the workflow owner needed here in prod
    manager = WorkflowManager(db)
    manager.cancel_workflow(workflow_id)
    return {"status": "cancelled"}

@router.post("/workflows/{workflow_id}/approve")
def approve_workflow(
    workflow_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    manager = WorkflowManager(db)
    manager.approve_patch(workflow_id)
    return {"status": "approved, workflow unblocked"}
