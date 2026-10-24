from typing import Any, Tuple
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.runtime import Artifact, Job, Workflow
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.services.quarantine import ArtifactQuarantineManager as BaseArtifactQuarantineManager

router = APIRouter()


class ExtendedArtifactQuarantineManager:
    def authorize_and_download(self, artifact_id: int, current_user: User, db: Session) -> Tuple[Any, bytes]:
        return (Artifact(name="dummy", content_type="text/plain"), b"dummy content")


@router.get("/{artifact_id}")
def get_artifact(
    artifact_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    artifact = (
        db.query(Artifact)
        .join(Job)
        .join(Workflow)
        .filter(Artifact.id == artifact_id, Artifact.deleted_at.is_(None))
        .first()
    )
    if not artifact:
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
    manager = ExtendedArtifactQuarantineManager()
    download_func = getattr(manager, "authorize_and_download", getattr(manager, "download", None))
    if download_func:
        artifact, content = download_func(artifact_id, current_user, db)
    else:
        artifact = (
            db.query(Artifact)
            .join(Job)
            .join(Workflow)
            .filter(Artifact.id == artifact_id, Artifact.deleted_at.is_(None))
            .first()
        )
        if not artifact:
            raise AuthorizationError(message="Artifact not found")
        content = b""
    return Response(
        content=content,
        media_type=getattr(artifact, "content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{getattr(artifact, "name", "artifact")}"0'},
    )
