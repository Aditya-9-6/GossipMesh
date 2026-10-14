from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from gossipmesh.api import deps
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.user import User

router = APIRouter()

class OrganizationResponse(BaseModel):
    id: int
    name: str

@router.get("/me", response_model=list[OrganizationResponse])
def read_organizations_me(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    return db.query(Organization).join(
        UserOrganization, Organization.id == UserOrganization.organization_id
    ).filter(
        UserOrganization.user_id == current_user.id
    ).all()
    user_orgs = db.query(UserOrganization).options(
        joinedload(UserOrganization.organization)
    ).filter(UserOrganization.user_id == current_user.id).all()
    return [org.organization for org in user_orgs]
