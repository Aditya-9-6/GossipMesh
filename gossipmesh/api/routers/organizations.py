from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User
from pydantic import BaseModel

router = APIRouter()

class OrganizationResponse(BaseModel):
    id: int
    name: str

@router.get("/me", response_model=List[OrganizationResponse])
def read_organizations_me(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    """Return the organizations associated with the authenticated user."""
    # A complete implementation would join UserOrganization
    return [org.organization for org in current_user.organizations]
