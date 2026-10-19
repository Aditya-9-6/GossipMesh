from typing import Any
import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.repository import Repository, IndexState
from gossipmesh.models.installations import GithubAppInstallation
from gossipmesh.repository.github import GitHubIntegration
from gossipmesh.core.config import settings
from gossipmesh.core.exceptions import AuthorizationError

router = APIRouter()
logger = logging.getLogger(__name__)

class RepositorySyncRequest(BaseModel):
    full_name: str
    installation_id: int
    organization_id: int

@router.post("/sync")
def sync_repository(
    request: RepositorySyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    is_member = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == request.organization_id,
        UserOrganization.is_suspended == False
    ).first()
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    installation = db.query(GithubAppInstallation).filter(
        GithubAppInstallation.installation_id == request.installation_id,
        GithubAppInstallation.organization_id == request.organization_id
    ).first()
    if not installation:
        raise AuthorizationError(message="Installation does not belong to the requested organization")

    def _sync_task(full_name: str, installation_id: int, org_id: int):
        github = GitHubIntegration()
        try:
            logger.info(f"Syncing {full_name} for installation {installation_id}")
            result = github.sync_repository(full_name, installation_id)
            logger.info(f"Sync successful for {full_name}: {result}")
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    background_tasks.add_task(_sync_task, request.full_name, request.installation_id, request.organization_id)
    return {"status": "accepted", "message": "Repository sync queued"}
