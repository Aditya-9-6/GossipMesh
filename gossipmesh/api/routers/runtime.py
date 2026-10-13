from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.runtime.workflow import WorkflowManager
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.api.rate_limit import rate_limit

router = APIRouter()

class CreateWorkflowRequest(BaseModel):
    organization_id: int
    repository_id: int
    agent_name: str

@router.post(
    "/workflows",
    status_code=201,
    dependencies=[Depends(rate_limit(limit_type="workflow", limit=5, window=60))]
)
def create_workflow(
    request: CreateWorkflowRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    # Ensure user has access to organization
    is_member = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == request.organization_id
    ).first()
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    manager = WorkflowManager(db)
    workflow = manager.create_workflow(request.organization_id, request.repository_id)
    job = manager.add_job(workflow.id, request.agent_name)

    # Normally this would enqueue a Celery task to begin execution
    return {"workflow_id": workflow.id, "job_id": job.id, "status": workflow.status}

@router.post(
    "/workflows/{workflow_id}/cancel",
    dependencies=[Depends(rate_limit(limit_type="workflow", limit=10, window=60))]
)
def cancel_workflow(
    workflow_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    # Proper auth check on the workflow owner needed here in prod
    manager = WorkflowManager(db)
    manager.cancel_workflow(workflow_id)
    return {"status": "cancelled"}

@router.post(
    "/workflows/{workflow_id}/approve",
    dependencies=[Depends(rate_limit(limit_type="workflow", limit=10, window=60))]
)
def approve_workflow(
    workflow_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    manager = WorkflowManager(db)
    manager.approve_patch(workflow_id)
    return {"status": "approved, workflow unblocked"}
