from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from gossipmesh.api import deps
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.enterprise.controls import DataExporter
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.user import User

router = APIRouter()

@router.get("/audit-logs/{tenant_id}")
def get_audit_logs(
    tenant_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    # Ensure user has access to organization
    is_member = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id,
        UserOrganization.organization_id == tenant_id
    ).first()
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    exporter = DataExporter()
    return {"logs": exporter.export_audit_logs(tenant_id)}
