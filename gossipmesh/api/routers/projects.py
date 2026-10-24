from typing import Any, List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization, OrganizationRole
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository
from gossipmesh.models.audit import AuditEvent

router = APIRouter()
logger = logging.getLogger(__name__)


class RepositorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    full_name: str
    default_branch: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    name: str
    description: Optional[str] = None
    repositories: List[RepositorySummary] = []


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


def log_audit_event(db: Session, action: str, actor_id: int, org_id: int, details: dict):
    event = AuditEvent(action=action, actor_id=actor_id, organization_id=org_id, details=details)
    db.add(event)


def require_project_member(project_id: int, db: Session, current_user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if getattr(current_user, "is_superuser", False):
        return project
    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == project.organization_id,
            UserOrganization.user_id == current_user.id,
            UserOrganization.is_suspended == False,
        )
        .first()
    )
    if not user_org:
        raise HTTPException(status_code=403, detail="Not authorized for this project's organization.")
    return project


def require_project_admin(project_id: int, db: Session, current_user: User) -> Project:
    project = require_project_member(project_id, db, current_user)
    if getattr(current_user, "is_superuser", False):
        return project
    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == project.organization_id,
            UserOrganization.user_id == current_user.id,
            UserOrganization.is_suspended == False,
        )
        .first()
    )
    if not user_org or user_org.role not in [OrganizationRole.admin, OrganizationRole.owner]:
        raise HTTPException(status_code=403, detail="Admin permissions required for this project action.")
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    project = require_project_member(project_id, db, current_user)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    project = require_project_admin(project_id, db, current_user)
    changes = {}
    if project_in.name is not None:
        project.name = project_in.name
        changes["name"] = project_in.name
    if project_in.description is not None:
        project.description = project_in.description
        changes["description"] = project_in.description
    log_audit_event(
        db,
        action="project.updated",
        actor_id=current_user.id,
        org_id=project.organization_id,
        details={"project_id": project.id, "changes": changes},
    )
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    project = require_project_admin(project_id, db, current_user)
    org_id = project.organization_id
    project_name = project.name
    for repo in project.repositories:
        repo.project_id = None
    db.delete(project)
    log_audit_event(
        db,
        action="project.deleted",
        actor_id=current_user.id,
        org_id=org_id,
        details={"project_id": project_id, "name": project_name},
    )
    db.commit()
    return {"message": "Project deleted successfully."}


@router.post("/{project_id}/repositories/{repo_id}", response_model=ProjectResponse)
def link_repository_to_project(
    project_id: int,
    repo_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    project = require_project_admin(project_id, db, current_user)
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    if repo.organization_id != project.organization_id:
        raise HTTPException(
            status_code=400,
            detail="Repository and Project must belong to the same organization.",
        )
    repo.project_id = project.id
    log_audit_event(
        db,
        action="project.repository_linked",
        actor_id=current_user.id,
        org_id=project.organization_id,
        details={"project_id": project.id, "repository_id": repo.id},
    )
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}/repositories/{repo_id}", response_model=ProjectResponse)
def unlink_repository_from_project(
    project_id: int,
    repo_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    project = require_project_admin(project_id, db, current_user)
    repo = db.query(Repository).filter(Repository.id == repo_id, Repository.project_id == project.id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not linked to this project.")
    repo.project_id = None
    log_audit_event(
        db,
        action="project.repository_unlinked",
        actor_id=current_user.id,
        org_id=project.organization_id,
        details={"project_id": project.id, "repository_id": repo.id},
    )
    db.commit()
    db.refresh(project)
    return project
