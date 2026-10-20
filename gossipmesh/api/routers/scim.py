from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.audit import AuditEvent
from pydantic import BaseModel

router = APIRouter()


# SCIM 2.0 Pydantic Models
class SCIMName(BaseModel):
    formatted: Optional[str] = None
    familyName: Optional[str] = None
    givenName: Optional[str] = None


class SCIMEmail(BaseModel):
    value: str
    type: str = "work"
    primary: bool = True


class SCIMUserCreate(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    userName: str
    name: Optional[SCIMName] = None
    emails: List[SCIMEmail]
    active: bool = True


class SCIMUserUpdate(SCIMUserCreate):
    pass


class SCIMUserPatchOperation(BaseModel):
    op: str  # "add", "remove", "replace"
    path: Optional[str] = None
    value: Any


class SCIMUserPatch(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    Operations: List[SCIMUserPatchOperation]


class SCIMMeta(BaseModel):
    resourceType: str
    location: Optional[str] = None


class SCIMUserResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:User"]
    id: str
    userName: str
    name: Optional[SCIMName] = None
    emails: List[SCIMEmail]
    active: bool
    meta: SCIMMeta


class SCIMListResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    totalResults: int
    itemsPerPage: int
    startIndex: int
    Resources: List[Any]


class SCIMError(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:api:messages:2.0:Error"]
    detail: str
    status: str


def _log_scim_audit(db: Session, action: str, org_id: int, details: dict):
    # Typically actor_id would come from the service account or API key, but we'll leave it as None or a system user for SCIM operations unless we map API keys to actors.
    event = AuditEvent(
        action=action,
        actor_id=1,  # System actor ID or logic to get it
        organization_id=org_id,
        details=details,
    )
    db.add(event)


def map_user_to_scim(user: User, user_org: UserOrganization) -> SCIMUserResponse:
    return SCIMUserResponse(
        id=str(user.id),
        userName=user.email,
        name=SCIMName(formatted=user.email),  # Simple fallback
        emails=[SCIMEmail(value=user.email)],
        active=not user_org.is_suspended and user.is_active,
        meta=SCIMMeta(resourceType="User"),
    )


@router.get(
    "/{org_id}/Users", response_model=SCIMListResponse, response_model_exclude_none=True
)
def list_users(
    org_id: int,
    startIndex: int = 1,
    count: int = 100,
    filter: Optional[str] = None,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    # Basic authorization check - API key must belong to a service account in the org
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    query = (
        db.query(User, UserOrganization)
        .join(UserOrganization, User.id == UserOrganization.user_id)
        .filter(UserOrganization.organization_id == org_id)
    )

    if filter:
        # Simple SCIM filter parsing for `userName eq "user@example.com"`
        # This is a very rudimentary parser for the demo
        if "userName eq" in filter:
            value = filter.split("eq")[1].strip().strip('"').strip("'")
            query = query.filter(User.email == value)
        elif 'emails[type eq "work" and value eq' in filter:  # okta test format
            # Basic fallback for complex email queries
            value = (
                filter.split("value eq")[1].split("]")[0].strip().strip('"').strip("'")
            )
            query = query.filter(User.email == value)

    total_results = query.count()

    # SCIM startIndex is 1-based
    db_offset = max(0, startIndex - 1)
    results = query.offset(db_offset).limit(count).all()

    resources = []
    for user, user_org in results:
        resources.append(map_user_to_scim(user, user_org))

    return SCIMListResponse(
        totalResults=total_results,
        itemsPerPage=len(resources),
        startIndex=startIndex,
        Resources=resources,
    )


@router.post(
    "/{org_id}/Users",
    response_model=SCIMUserResponse,
    response_model_exclude_none=True,
    status_code=201,
)
def create_user(
    org_id: int,
    user_in: SCIMUserCreate,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    # The userName is typically the email in Okta/Entra setups for SaaS
    email = user_in.userName
    if user_in.emails and len(user_in.emails) > 0:
        email = user_in.emails[0].value

    # Check if user already exists in DB
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create new global user (mock password or no password)
        user = User(email=email, is_active=True)
        db.add(user)
        db.flush()

    # Check if user is already in the org
    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.user_id == user.id,
        )
        .first()
    )

    if user_org:
        # Returning 409 Conflict per SCIM spec when resource exists
        raise HTTPException(
            status_code=409, detail=f"User {email} already exists in organization"
        )

    # Add user to org
    user_org = UserOrganization(
        user_id=user.id,
        organization_id=org_id,
        role="member",
        is_suspended=not user_in.active,
    )
    db.add(user_org)

    _log_scim_audit(
        db, "scim.user.created", org_id, {"user_id": user.id, "email": email}
    )
    db.commit()
    db.refresh(user)
    db.refresh(user_org)

    return map_user_to_scim(user, user_org)


@router.get(
    "/{org_id}/Users/{id}",
    response_model=SCIMUserResponse,
    response_model_exclude_none=True,
)
def get_user(
    org_id: int,
    id: str,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    try:
        user_id = int(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.user_id == user_id,
        )
        .first()
    )

    if not user_org:
        raise HTTPException(status_code=404, detail="User not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return map_user_to_scim(user, user_org)


@router.put(
    "/{org_id}/Users/{id}",
    response_model=SCIMUserResponse,
    response_model_exclude_none=True,
)
def update_user(
    org_id: int,
    id: str,
    user_in: SCIMUserUpdate,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    try:
        user_id = int(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.user_id == user_id,
        )
        .first()
    )

    if not user_org:
        raise HTTPException(status_code=404, detail="User not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update logic
    if user_in.emails and len(user_in.emails) > 0:
        user.email = user_in.emails[0].value

    user_org.is_suspended = not user_in.active

    _log_scim_audit(
        db, "scim.user.updated", org_id, {"user_id": user.id, "active": user_in.active}
    )
    db.commit()
    db.refresh(user)
    db.refresh(user_org)

    return map_user_to_scim(user, user_org)


@router.patch(
    "/{org_id}/Users/{id}",
    response_model=SCIMUserResponse,
    response_model_exclude_none=True,
)
def patch_user(
    org_id: int,
    id: str,
    patch_in: SCIMUserPatch,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    try:
        user_id = int(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.user_id == user_id,
        )
        .first()
    )

    if not user_org:
        raise HTTPException(status_code=404, detail="User not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Rudimentary PATCH support (mainly for active status which Entra/Okta uses for deprovisioning)
    for op in patch_in.Operations:
        if op.op.lower() == "replace":
            if op.path == "active" or (
                isinstance(op.value, dict) and "active" in op.value
            ):
                # Handle `{"op": "replace", "value": {"active": False}}` or `{"op": "replace", "path": "active", "value": False}`
                active_val = op.value
                if isinstance(op.value, dict) and "active" in op.value:
                    active_val = op.value["active"]
                elif isinstance(op.value, str):
                    active_val = op.value.lower() == "true"
                user_org.is_suspended = not active_val

    _log_scim_audit(db, "scim.user.patched", org_id, {"user_id": user.id})
    db.commit()
    db.refresh(user)
    db.refresh(user_org)

    return map_user_to_scim(user, user_org)


@router.delete("/{org_id}/Users/{id}", status_code=204)
def delete_user(
    org_id: int,
    id: str,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    try:
        user_id = int(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="User not found")

    user_org = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.organization_id == org_id,
            UserOrganization.user_id == user_id,
        )
        .first()
    )

    if not user_org:
        raise HTTPException(status_code=404, detail="User not found")

    # Hard delete from org (deprovisioned users lose access immediately)
    db.delete(user_org)
    _log_scim_audit(db, "scim.user.deleted", org_id, {"user_id": user_id})
    db.commit()

    return None


# SCIM Groups (Roles) mapping
class SCIMGroupResponse(BaseModel):
    schemas: List[str] = ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    id: str
    displayName: str
    meta: SCIMMeta


@router.get(
    "/{org_id}/Groups",
    response_model=SCIMListResponse,
    response_model_exclude_none=True,
)
def list_groups(
    org_id: int,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    # In our model, "Groups" are actually "Roles" within the org (admin, member)
    roles = ["admin", "member"]
    resources = []

    for role in roles:
        resources.append(
            SCIMGroupResponse(
                id=role,
                displayName=role.capitalize(),
                meta=SCIMMeta(resourceType="Group"),
            )
        )

    return SCIMListResponse(
        totalResults=len(resources),
        itemsPerPage=len(resources),
        startIndex=1,
        Resources=resources,
    )


@router.get(
    "/{org_id}/Groups/{id}",
    response_model=SCIMGroupResponse,
    response_model_exclude_none=True,
)
def get_group(
    org_id: int,
    id: str,
    api_key=Depends(deps.get_scim_token),
    db: Session = Depends(deps.get_db),
):
    from gossipmesh.models.service_account import ServiceAccount

    account = (
        db.query(ServiceAccount)
        .filter(ServiceAccount.id == api_key.service_account_id)
        .first()
    )
    if not account or account.organization_id != org_id:
        raise HTTPException(
            status_code=403, detail="Not authorized for this organization"
        )

    if id not in ["admin", "member"]:
        raise HTTPException(status_code=404, detail="Group not found")

    return SCIMGroupResponse(
        id=id, displayName=id.capitalize(), meta=SCIMMeta(resourceType="Group")
    )
