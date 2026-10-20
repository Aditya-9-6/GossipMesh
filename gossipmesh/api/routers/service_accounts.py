from typing import Any, List, Optional
from datetime import datetime, timezone, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.service_account import ServiceAccount, APIKey
from gossipmesh.models.audit import AuditEvent
from gossipmesh.core.security import get_password_hash

router = APIRouter()


class ServiceAccountCreate(BaseModel):
    organization_id: int
    name: str
    description: Optional[str] = None


class ServiceAccountResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    description: Optional[str] = None


class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str]
    expires_in_days: Optional[int] = None


class APIKeyCreateResponse(BaseModel):
    id: int
    name: str
    prefix: str
    key: str  # Only returned once
    scopes: List[str]
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    is_revoked: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime


def _ensure_org_access(db: Session, user_id: int, organization_id: int):
    user_org = (
        db.query(UserOrganization)
        .filter(UserOrganization.user_id == user_id, UserOrganization.organization_id == organization_id)
        .first()
    )
    if not user_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions for this organization"
        )
    return user_org


@router.post("/", response_model=ServiceAccountResponse)
def create_service_account(
    account_in: ServiceAccountCreate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    _ensure_org_access(db, current_user.id, account_in.organization_id)

    account = ServiceAccount(
        organization_id=account_in.organization_id, name=account_in.name, description=account_in.description
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    # Audit log
    audit_event = AuditEvent(
        action="service_account.create",
        actor_id=current_user.id,
        organization_id=account.organization_id,
        details={"service_account_id": account.id, "name": account.name},
    )
    db.add(audit_event)
    db.commit()

    return account


@router.get("/", response_model=List[ServiceAccountResponse])
def read_service_accounts(
    organization_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    _ensure_org_access(db, current_user.id, organization_id)

    accounts = db.query(ServiceAccount).filter(ServiceAccount.organization_id == organization_id).all()
    return accounts


def generate_api_key() -> tuple[str, str, str]:
    """Generates a raw key, prefix, and hashed key."""
    # Prefix is up to 16 chars to prevent collisions.
    raw_key = f"gm_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:16]
    hashed_key = get_password_hash(raw_key)
    return raw_key, prefix, hashed_key


@router.post("/{service_account_id}/keys", response_model=APIKeyCreateResponse)
def create_api_key(
    service_account_id: int,
    key_in: APIKeyCreate,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    account = db.query(ServiceAccount).filter(ServiceAccount.id == service_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Service account not found")

    _ensure_org_access(db, current_user.id, account.organization_id)

    raw_key, prefix, hashed_key = generate_api_key()

    expires_at = None
    if key_in.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=key_in.expires_in_days)

    api_key = APIKey(
        service_account_id=account.id,
        name=key_in.name,
        prefix=prefix,
        hashed_key=hashed_key,
        scopes=key_in.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Audit log
    audit_event = AuditEvent(
        action="api_key.create",
        actor_id=current_user.id,
        organization_id=account.organization_id,
        details={"service_account_id": account.id, "api_key_id": api_key.id, "prefix": prefix},
    )
    db.add(audit_event)
    db.commit()

    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        key=raw_key,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
    )


@router.get("/{service_account_id}/keys", response_model=List[APIKeyResponse])
def read_api_keys(
    service_account_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    account = db.query(ServiceAccount).filter(ServiceAccount.id == service_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Service account not found")

    _ensure_org_access(db, current_user.id, account.organization_id)

    keys = db.query(APIKey).filter(APIKey.service_account_id == account.id).all()
    return keys


@router.delete("/keys/{key_id}", response_model=dict)
def revoke_api_key(
    key_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    account = db.query(ServiceAccount).filter(ServiceAccount.id == api_key.service_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Service account not found")
    _ensure_org_access(db, current_user.id, account.organization_id)

    api_key.is_revoked = True
    db.commit()

    # Audit log
    audit_event = AuditEvent(
        action="api_key.revoke",
        actor_id=current_user.id,
        organization_id=account.organization_id,
        details={"service_account_id": account.id, "api_key_id": api_key.id, "prefix": api_key.prefix},
    )
    db.add(audit_event)
    db.commit()

    return {"status": "success", "message": "API key revoked"}
