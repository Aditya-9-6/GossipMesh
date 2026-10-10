from typing import Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.repository import Repository, IndexState
from gossipmesh.repository.github import GitHubIntegration
from gossipmesh.core.config import settings

router = APIRouter()

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
    # In a full implementation, we'd trigger a Celery task here.
    # We are using FastAPI BackgroundTasks for simplicity in this endpoint demonstration.

    # Simple auth check: verify user belongs to the requested organization
    user_org_ids = [org.organization_id for org in current_user.organizations]
    if request.organization_id not in user_org_ids:
        raise HTTPException(status_code=403, detail="Not authorized for this organization")

    def _sync_task(full_name: str, installation_id: int, org_id: int):
        # We would use real secrets in production
        github = GitHubIntegration(app_id="mock_app_id", private_key="mock_key")
        try:
            repo_data = github.sync_repository(full_name, installation_id)
            # Update database with repo_data here...
        except Exception as e:
            # Log error
            pass

    background_tasks.add_task(_sync_task, request.full_name, request.installation_id, request.organization_id)
    return {"status": "accepted", "message": "Repository sync queued"}
