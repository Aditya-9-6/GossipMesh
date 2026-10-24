from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.enterprise.controls import DataExporter
from gossipmesh.enterprise.outcome_report import AutomationOutcomeReporter

router = APIRouter()


@router.get("/audit-logs/{tenant_id}")
def get_audit_logs(
    tenant_id: int, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    is_member = (
        db.query(UserOrganization)
        .filter(UserOrganization.user_id == current_user.id, UserOrganization.organization_id == tenant_id)
        .first()
    )
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    exporter = DataExporter()
    return {"logs": exporter.export_audit_logs(tenant_id)}


@router.get("/reports/outcome/{tenant_id}")
def get_outcome_report(
    tenant_id: int,
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    repo: Optional[str] = Query(None),
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """Retrieves operational automation outcome metrics for the tenant."""
    is_member = (
        db.query(UserOrganization)
        .filter(UserOrganization.user_id == current_user.id, UserOrganization.organization_id == tenant_id)
        .first()
    )
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    reporter = AutomationOutcomeReporter()
    if period == "weekly":
        report = reporter.get_weekly_report(tenant_id=tenant_id, repo=repo)
    else:
        report = reporter.get_daily_report(tenant_id=tenant_id, repo=repo)

    return report.to_dict()
