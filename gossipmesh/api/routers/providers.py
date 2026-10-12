from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.provider import ProviderCredential
from gossipmesh.models.organization import UserOrganization
from gossipmesh.core.security import encrypt_string, decrypt_string
from gossipmesh.providers.manager import ProviderManager
from gossipmesh.providers.models import ProviderHealth

router = APIRouter()

class ProviderRegistration(BaseModel):
    name: str
    api_key: str | None = None
    base_url: str | None = None

def _get_provider_manager_for_org(db: Session, org_id: int) -> ProviderManager:
    """Instantiates a ProviderManager and loads the organization's saved credentials."""
    manager = ProviderManager()
    credentials = db.query(ProviderCredential).filter(ProviderCredential.organization_id == org_id).all()

    for cred in credentials:
        try:
            # We assume Ollama uses base_url instead of api_key if needed, but for simplicity here:
            decrypted_key = decrypt_string(cred.encrypted_key) if cred.encrypted_key else None
            manager.register_provider(cred.provider_name, decrypted_key)
        except Exception:
            pass # Skip failed decryptions in this simple example

    return manager

@router.post("/register", status_code=201)
def register_provider(
    registration: ProviderRegistration,
    organization_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Registers and persists a provider credential for the organization."""
    is_member = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == organization_id
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="Not authorized for this organization")

    try:
        # Verify it can be instantiated
        manager = ProviderManager()
        kwargs = {}
        if registration.base_url:
            kwargs["base_url"] = registration.base_url
        manager.register_provider(registration.name, registration.api_key, **kwargs)

        # Persist to database
        encrypted_key = encrypt_string(registration.api_key) if registration.api_key else ""

        cred = db.query(ProviderCredential).filter(
            ProviderCredential.organization_id == organization_id,
            ProviderCredential.provider_name == registration.name
        ).first()

        if cred:
            cred.encrypted_key = encrypted_key
        else:
            cred = ProviderCredential(
                organization_id=organization_id,
                provider_name=registration.name,
                encrypted_key=encrypted_key
            )
            db.add(cred)
        db.commit()

        return {"status": "success", "message": f"Provider {registration.name} registered and saved."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/health", response_model=Dict[str, ProviderHealth])
async def get_providers_health(
    organization_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Returns the health status of providers registered for the organization."""
    is_member = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == organization_id
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="Not authorized for this organization")

    manager = _get_provider_manager_for_org(db, organization_id)
    return await manager.check_all_health()
