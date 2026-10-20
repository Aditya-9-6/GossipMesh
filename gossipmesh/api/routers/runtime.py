from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.runtime import Workflow
from gossipmesh.runtime.workflow import WorkflowManager
from gossipmesh.core.exceptions import AuthorizationError

router = APIRouter()


class CreateWorkflowRequest(BaseModel):
    organization_id: int
    repository_id: int
    agent_name: str


@router.post("/workflows", status_code=201)
def create_workflow(
    request: CreateWorkflowRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    # Ensure user has access to organization
    is_member = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == current_user.id, UserOrganization.organization_id == request.organization_id
        )
        .first()
    )
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    manager = WorkflowManager(db)
    workflow, job = manager.create_workflow_with_job(
        request.organization_id,
        request.repository_id,
        request.agent_name,
        actor_id=current_user.id,
    )

    # Normally this would enqueue a Celery task to begin execution
    return {"workflow_id": workflow.id, "job_id": job.id, "status": workflow.status}


@router.post("/workflows/{workflow_id}/cancel")
def cancel_workflow(
    workflow_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        # Depending on app convention, we could return 404 or gracefully ignore. Returning generic error for now.
        return {"status": "error", "message": "Workflow not found"}

    is_member = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == current_user.id, UserOrganization.organization_id == workflow.organization_id
        )
        .first()
    )
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    manager = WorkflowManager(db)
    manager.cancel_workflow(workflow_id, actor_id=current_user.id)
    return {"status": "cancelled"}


@router.post("/workflows/{workflow_id}/approve")
def approve_workflow(
    workflow_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        return {"status": "error", "message": "Workflow not found"}

    is_member = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == current_user.id, UserOrganization.organization_id == workflow.organization_id
        )
        .first()
    )
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    manager = WorkflowManager(db)
    manager.approve_patch(workflow_id, actor_id=current_user.id)
    return {"status": "approved, workflow unblocked"}
