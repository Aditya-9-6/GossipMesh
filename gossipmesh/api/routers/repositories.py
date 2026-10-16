from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.repository import Repository, IndexState, GithubAppInstallation
from gossipmesh.repository.github import GitHubIntegration
from gossipmesh.core.config import settings
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.models.jobs import BackgroundJob
from gossipmesh.worker.tasks import sync_repository_task
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SyncRequest(BaseModel):
    full_name: str
    installation_id: int
    organization_id: int

@router.post("/sync", status_code=202)
def sync_repository(
    request: SyncRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Queues a background task to sync repository metadata from GitHub."""
    is_member = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == request.organization_id
    ).first()
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    # Validate that an installation belongs to the requested organization.
    installation = db.query(GithubAppInstallation).filter(
        GithubAppInstallation.installation_id == request.installation_id,
        GithubAppInstallation.organization_id == request.organization_id
    ).first()
    if not installation:
        raise AuthorizationError(message="Installation does not belong to the requested organization")

    task_id = str(uuid.uuid4())

    job_record = BackgroundJob(
        task_id=task_id,
        task_name="sync_repository_task",
        organization_id=request.organization_id,
        user_id=current_user.id
    )
    db.add(job_record)
    db.commit()

    sync_repository_task.apply_async(
        args=[request.full_name, request.installation_id, request.organization_id],
        task_id=task_id
    )

    return {"status": "accepted", "message": "Repository sync queued", "job_id": task_id}
