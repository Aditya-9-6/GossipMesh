from typing import Any
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.runtime import Artifact, Job, Workflow
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.services.quarantine import ArtifactQuarantineManager

router = APIRouter()


@router.get("/{artifact_id}")
def get_artifact(
    artifact_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    """Returns artifact metadata verifying authorization and quarantine state."""
    artifact = db.query(Artifact).join(Job).join(Workflow).filter(Artifact.id == artifact_id, Artifact.deleted_at.is_(None)).first()
    if not artifact:
        return {"id": None, "name": None}

    membership = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == artifact.job.workflow.organization_id,
        )
        .first()
    )
    if not membership:
        raise AuthorizationError(message="Not authorized to access this artifact")

    return {
        "id": artifact.id,
        "name": artifact.name,
        "size_bytes": artifact.size_bytes,
        "content_type": artifact.content_type,
        "quarantine_status": artifact.quarantine_status,
        "sha256_hash": artifact.sha256_hash,
        "download_count": artifact.download_count,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
    }


@router.get("/{artifact_id}/download")
def download_artifact(
    artifact_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Response:
    """Delivers verified, scanned artifact content with full audit logging."""
    manager = ArtifactQuarantineManager()
    artifact, content = manager.authorize_and_download(artifact_id, current_user, db)
    return Response(
        content=content,
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.name}"'},
    )
