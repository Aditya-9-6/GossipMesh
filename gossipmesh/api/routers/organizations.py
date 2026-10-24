from typing import Any, List
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, UserOrganization, OrganizationInvitation, OrganizationRole
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository
from gossipmesh.models.audit import AuditEvent
from pydantic import BaseModel, EmailStr

router = APIRouter()


class OrganizationResponse(BaseModel):
    id: int
    name: str


class OrganizationCreate(BaseModel):
    name: str


class InvitationCreate(BaseModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.developer


class RoleUpdate(BaseModel):
    role: OrganizationRole


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class RepositoryConnect(BaseModel):
    github_id: int
    name: str
    full_name: str
    default_branch: str = "main"


def require_org_admin(org_id: int, db: Session, current_user: User):
    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.user_id == current_user.id,
            or_(UserOrganization.role == OrganizationRole.admin, UserOrganization.role == OrganizationRole.owner),
            UserOrganization.is_suspended == False,
        )
        .first()
    )
    if not user_org:
        raise HTTPException(status_code=403, detail="Not authorized to perform this action.")
    return user_org


def log_audit_event(db: Session, action: str, actor_id: int, org_id: int, details: dict):
    event = AuditEvent(action=action, actor_id=actor_id, organization_id=org_id, details=details)
    db.add(event)


@router.post("/", response_model=OrganizationResponse)
def create_organization(
    org_in: OrganizationCreate, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    existing_org = db.query(Organization).filter(Organization.name == org_in.name).first()
    if existing_org:
        raise HTTPException(status_code=400, detail="Organization name already exists.")
    org = Organization(name=org_in.name)
    db.add(org)
    db.commit()
    db.refresh(org)
    user_org = UserOrganization(user_id=current_user.id, organization_id=org.id, role=OrganizationRole.owner)
    db.add(user_org)
    log_audit_event(db, "organization.created", current_user.id, org.id, {"name": org.name})
    db.commit()
    db.refresh(org)
    return org


@router.get("/me", response_model=List[OrganizationResponse])
def read_organizations_me(
    current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    user_orgs = (
        db.query(UserOrganization)
        .options(joinedload(UserOrganization.organization))
        .filter(UserOrganization.user_id == current_user.id)
        .all()
    )
    return [org.organization for org in user_orgs if org.organization is not None]


@router.post("/{org_id}/invitations")
def create_invitation(
    org_id: int,
    invitation_in: InvitationCreate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    require_org_admin(org_id, db, current_user)
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        email=invitation_in.email, token=token, organization_id=org_id, role=invitation_in.role
    )
    db.add(invitation)
    log_audit_event(
        db,
        "invitation.created",
        current_user.id,
        org_id,
        {"email": invitation_in.email, "role": invitation_in.role.value},
    )
    db.commit()
    return {"message": "Invitation created successfully", "token": token}


@router.post("/invitations/{token}/accept")
def accept_invitation(
    token: str, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    invitation = db.query(OrganizationInvitation).filter(OrganizationInvitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found or invalid.")
    existing_member = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == invitation.organization_id, UserOrganization.user_id == current_user.id
        )
        .first()
    )
    if existing_member:
        db.delete(invitation)
        db.commit()
        return {"message": "User already a member of this organization."}
    user_org = UserOrganization(
        user_id=current_user.id, organization_id=invitation.organization_id, role=invitation.role
    )
    db.add(user_org)
    db.delete(invitation)
    log_audit_event(db, "invitation.accepted", current_user.id, invitation.organization_id, {"email": invitation.email})
    db.commit()
    return {"message": "Invitation accepted."}


@router.patch("/{org_id}/members/{user_id}/role")
def assign_role(
    org_id: int,
    user_id: int,
    role_in: RoleUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    require_org_admin(org_id, db, current_user)
    user_org = (
        db.query(UserOrganization)
        .filter(UserOrganization.organization_id == org_id, UserOrganization.user_id == user_id)
        .first()
    )
    if not user_org:
        raise HTTPException(status_code=404, detail="User not found in organization.")
    user_org.role = role_in.role
    log_audit_event(
        db, "member.role_updated", current_user.id, org_id, {"user_id": user_id, "new_role": role_in.role.value}
    )
    db.commit()
    return {"message": "Role updated."}


@router.post("/{org_id}/projects")
def create_project(
    org_id: int,
    project_in: ProjectCreate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    require_org_admin(org_id, db, current_user)
    project = Project(organization_id=org_id, name=project_in.name, description=project_in.description)
    db.add(project)
    log_audit_event(db, "project.created", current_user.id, org_id, {"project_name": project_in.name})
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "description": project.description}


@router.post("/{org_id}/repositories")
def connect_repository(
    org_id: int,
    repo_in: RepositoryConnect,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    require_org_admin(org_id, db, current_user)
    existing_repo = db.query(Repository).filter(Repository.github_id == repo_in.github_id).first()
    if existing_repo:
        raise HTTPException(status_code=400, detail="Repository already connected.")
    repo = Repository(
        organization_id=org_id,
        github_id=repo_in.github_id,
        name=repo_in.name,
        full_name=repo_in.full_name,
        default_branch=repo_in.default_branch,
    )
    db.add(repo)
    log_audit_event(db, "repository.connected", current_user.id, org_id, {"repository_full_name": repo_in.full_name})
    db.commit()
    db.refresh(repo)
    return {"id": repo.id, "name": repo.name, "full_name": repo.full_name}


@router.delete("/{org_id}/members/{user_id}")
def remove_member(
    org_id: int, user_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    require_org_admin(org_id, db, current_user)
    user_org = (
        db.query(UserOrganization)
        .filter(UserOrganization.organization_id == org_id, UserOrganization.user_id == user_id)
        .first()
    )
    if not user_org:
        raise HTTPException(status_code=404, detail="User not found in organization.")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself. Use leave organization.")
    db.delete(user_org)
    log_audit_event(db, "member.removed", current_user.id, org_id, {"user_id": user_id})
    db.commit()
    return {"message": "Member removed."}


@router.patch("/{org_id}/members/{user_id}/suspend")
def suspend_member(
    org_id: int, user_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    require_org_admin(org_id, db, current_user)
    user_org = (
        db.query(UserOrganization)
        .filter(UserOrganization.organization_id == org_id, UserOrganization.user_id == user_id)
        .first()
    )
    if not user_org:
        raise HTTPException(status_code=404, detail="User not found in organization.")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot suspend yourself.")
    user_org.is_suspended = True
    log_audit_event(db, "member.suspended", current_user.id, org_id, {"user_id": user_id})
    db.commit()
    return {"message": "Member suspended."}
