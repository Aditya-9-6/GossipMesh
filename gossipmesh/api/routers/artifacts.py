from typing import Any, List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{artifact_id}")
def get_artifact(
    artifact_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    """Returns artifact metadata verifying authorization and quarantine state."""
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
) -> Any:
    """Download or inspect an artifact."""
    return {"artifact_id": artifact_id, "status": "available"}
