from typing import Any, Dict, List, Optional, Tuple
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization, OrganizationRole
from gossipmesh.models.repository import Repository, RepositoryPolicy, IndexState
from gossipmesh.models.audit import AuditEvent
from gossipmesh.repository.github import GitHubIntegration
from gossipmesh.core.exceptions import AuthorizationError

router = APIRouter()
logger = logging.getLogger(__name__)


class SyncRequest(BaseModel):
    full_name: str
    installation_id: int
    organization_id: int


class BranchSelectRequest(BaseModel):
    default_branch: str = Field(..., min_length=1, description="New default branch name")


class RepositoryPolicyUpdate(BaseModel):
    branch_protection_enabled: Optional[bool] = None
    auto_merge_enabled: Optional[bool] = None
    auto_fix_enabled: Optional[bool] = None
    require_review_approval: Optional[bool] = None
    require_review: Optional[bool] = None
    min_approvals: Optional[int] = Field(None, ge=1, le=10)
    allowed_target_branches: Optional[List[str]] = None
    max_diff_lines: Optional[int] = Field(None, ge=10, le=100000)
    scan_frequency_hours: Optional[int] = Field(None, ge=1, le=720)
    custom_rules: Optional[Dict[str, Any]] = None


class RepositoryPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    repository_id: int
    branch_protection_enabled: bool
    auto_merge_enabled: bool
    require_review_approval: bool
    min_approvals: int
    allowed_target_branches: List[str]
    max_diff_lines: int
    scan_frequency_hours: int
    custom_rules: Dict[str, Any]


class RepositoryDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    project_id: Optional[int] = None
    github_id: int
    name: str
    full_name: str
    default_branch: str
    policy: Optional[RepositoryPolicyResponse] = None


def log_audit_event(db: Session, action: str, actor_id: int, org_id: int, details: dict):
    event = AuditEvent(action=action, actor_id=actor_id, organization_id=org_id, details=details)
    db.add(event)


def get_user_repo_membership(
    repo_id: int, db: Session, current_user: User
) -> Tuple[Repository, Optional[UserOrganization]]:
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if getattr(current_user, "is_superuser", False):
        return repo, None
    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == repo.organization_id,
            UserOrganization.user_id == current_user.id,
            UserOrganization.is_suspended == False,
        )
        .first()
    )
    if not user_org:
        raise HTTPException(status_code=403, detail="Not authorized for this repository's organization.")
    return repo, user_org


def require_repo_admin(repo_id: int, db: Session, current_user: User) -> Tuple[Repository, Optional[UserOrganization]]:
    repo, user_org = get_user_repo_membership(repo_id, db, current_user)
    if getattr(current_user, "is_superuser", False):
        return repo, user_org
    role_val = getattr(user_org, "role", None)
    allowed_admin_roles = [
        OrganizationRole.ADMIN,
        OrganizationRole.OWNER,
    ]
    if role_val not in allowed_admin_roles:
        raise HTTPException(status_code=403, detail="Admin permissions required for this repository action.")
    return repo, user_org


def require_repo_writer(repo_id: int, db: Session, current_user: User) -> Tuple[Repository, Optional[UserOrganization]]:
    repo, user_org = get_user_repo_membership(repo_id, db, current_user)
    if getattr(current_user, "is_superuser", False):
        return repo, user_org
    role_val = getattr(user_org, "role", None)
    allowed_writer_roles = [
        OrganizationRole.ADMIN,
        OrganizationRole.OWNER,
        OrganizationRole.DEVELOPER,
    ]
    if role_val not in allowed_writer_roles:
        raise HTTPException(status_code=403, detail="Write permissions required for this repository action.")
    return repo, user_org


def get_or_create_default_policy(repo: Repository, db: Session) -> RepositoryPolicy:
    policy = db.query(RepositoryPolicy).filter(RepositoryPolicy.repository_id == repo.id).first()
    if not policy:
        policy = RepositoryPolicy(
            repository_id=repo.id,
            branch_protection_enabled=True,
            auto_merge_enabled=False,
            require_review_approval=True,
            min_approvals=1,
            allowed_target_branches=["main", "master"],
            max_diff_lines=500,
            scan_frequency_hours=24,
            custom_rules={},
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
    return policy


@router.post("/sync", status_code=202)
def sync_repository(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    is_member = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == current_user.id, UserOrganization.organization_id == request.organization_id
        )
        .first()
    )
    if not is_member and not getattr(current_user, "is_superuser", False):
        raise AuthorizationError(message="Not authorized for this organization")
    return {"status": "accepted", "message": "Repository sync queued"}


@router.get("/{repo_id}", response_model=RepositoryDetailResponse)
def get_repository(
    repo_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    repo, _ = get_user_repo_membership(repo_id, db, current_user)
    get_or_create_default_policy(repo, db)
    db.refresh(repo)
    return repo


@router.patch("/{repo_id}/branch", response_model=RepositoryDetailResponse)
def select_branch(
    repo_id: int,
    body: BranchSelectRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    repo, _ = require_repo_writer(repo_id, db, current_user)
    repo.default_branch = body.default_branch
    db.commit()
    db.refresh(repo)
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_200_OK)
def remove_repository(
    repo_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    repo, _ = require_repo_admin(repo_id, db, current_user)
    db.query(RepositoryPolicy).filter(RepositoryPolicy.repository_id == repo.id).delete()
    db.delete(repo)
    db.commit()
    return {"message": "Repository removed successfully."}


@router.get("/{repo_id}/policy", response_model=RepositoryPolicyResponse)
def get_repository_policy(
    repo_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    repo, _ = get_user_repo_membership(repo_id, db, current_user)
    return get_or_create_default_policy(repo, db)


@router.put("/{repo_id}/policy", response_model=RepositoryPolicyResponse)
@router.patch("/{repo_id}/policy", response_model=RepositoryPolicyResponse)
def update_repository_policy(
    repo_id: int,
    policy_in: RepositoryPolicyUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    repo, _ = require_repo_admin(repo_id, db, current_user)
    policy = get_or_create_default_policy(repo, db)
    if policy_in.min_approvals is not None:
        policy.min_approvals = policy_in.min_approvals
    db.commit()
    db.refresh(policy)
    return policy
