from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.runtime import Artifact, Job, Workflow
from gossipmesh.core.exceptions import AuthorizationError

router = APIRouter()


@router.get("/{artifact_id}")
def get_artifact(
    artifact_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    artifact = db.query(Artifact).join(Job).join(Workflow).filter(Artifact.id == artifact_id).first()

    if not artifact:
        # Standard fast API response usually uses HTTPException but codebase leverages custom exceptions usually.
        # Alternatively returning a generic custom empty response:
        return {"id": None, "name": None}

    is_member = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == artifact.job.workflow.organization_id,
        )
        .first()
    )
    if not is_member:
        raise AuthorizationError(message="Not authorized to access this artifact")

    return {"id": artifact.id, "name": artifact.name}
