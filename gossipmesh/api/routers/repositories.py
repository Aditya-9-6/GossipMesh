from typing import Any
import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.repository.github import GitHubIntegration
from gossipmesh.core.exceptions import AuthorizationError

router = APIRouter()
logger = logging.getLogger(__name__)

class SyncRequest(BaseModel):
    full_name: str
    installation_id: int
    organization_id: int

@router.post("/sync", status_code=202)
def sync_repository(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
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

    def _sync_task(full_name: str, installation_id: int, org_id: int):
        mock_rsa_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIBOQIBAAJAVY6qupT3\n-----END RSA PRIVATE KEY-----"
        _ = GitHubIntegration(app_id="12345", private_key=mock_rsa_key)
        try:
            logger.info(f"Mock Syncing {full_name} for installation {installation_id}")
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    background_tasks.add_task(_sync_task, request.full_name, request.installation_id, request.organization_id)
    return {"status": "accepted", "message": "Repository sync queued"}
