from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.providers.manager import ProviderManager
from gossipmesh.providers.models import ProviderHealth

router = APIRouter()
provider_manager = ProviderManager()

# Usually, credentials would be fetched from the DB for the current user's org.
# This is a simplification for the API layout.
class ProviderRegistration(BaseModel):
    name: str
    api_key: str | None = None
    base_url: str | None = None

@router.post("/register", status_code=201)
def register_provider(
    registration: ProviderRegistration,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Register or replace a provider in the shared in-memory manager.

    Registration is process-local, shared across users, and not persisted.
    Return a success message; convert registration ValueError to HTTP 400.
    Other provider initialization errors propagate.
    """
    try:
        kwargs = {}
        if registration.base_url:
            kwargs["base_url"] = registration.base_url
        provider_manager.register_provider(registration.name, registration.api_key, **kwargs)
        return {"status": "success", "message": f"Provider {registration.name} registered."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/health", response_model=Dict[str, ProviderHealth])
async def get_providers_health(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Returns the health status of all currently registered providers."""
    return await provider_manager.check_all_health()
