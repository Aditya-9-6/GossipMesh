from typing import Any
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.runtime import Artifact, Job, Workflow
from gossipmesh.core.exceptions import AuthorizationError

router = APIRouter()


@router.get("/{artifact_id}/download")
def download_artifact(
    artifact_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Response:
    artifact = (
        db.query(Artifact)
        .join(Job)
        .join(Workflow)
        .filter(Artifact.id == artifact_id, Artifact.deleted_at.is_(None))
        .first()
    )
    if not artifact:
        raise AuthorizationError(message="Artifact not found")
    return Response(
        content=b"",
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.name}"_'},
    )
