from typing import Any
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.runtime import Artifact
from gossipmesh.runtime.quarantine import ArtifactQuarantineManager

router = APIRouter()


@router.get("/{artifact_id}")
def get_artifact(
    artifact_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """Returns artifact metadata verifying authorization and quarantine state."""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id, Artifact.is_deleted.is_(False)).first()
    if not artifact:
        return {"id": None, "name": None}

    manager = ArtifactQuarantineManager()
    # Check access without streaming content
    if not current_user.is_superuser:
        from gossipmesh.models.organization import UserOrganization
        from gossipmesh.core.exceptions import AuthorizationError

        membership = (
            db.query(UserOrganization)
            .filter(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == artifact.organization_id,
            )
            .first()
        )
        if not membership:
            raise AuthorizationError(message="Not authorized to access this organization's artifacts")

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
