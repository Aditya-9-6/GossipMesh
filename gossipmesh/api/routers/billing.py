"""
Billing API Endpoints (Task 87 & Task 90).

Provides checkout, customer portal, subscription management, invoices,
usage reporting, and signature-verified webhook endpoints.
Restricts billing actions strictly to billing administrators and emits
audit trail records for every billing action.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from gossipmesh.api import deps
from gossipmesh.billing.stripe_service import StripeBillingService
from gossipmesh.billing.usage_metering import UsageMeteringService
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.organization import OrganizationRole, UserOrganization
from gossipmesh.models.user import User

router = APIRouter()
billing_service = StripeBillingService()


class CheckoutRequest(BaseModel):
    organization_id: int
    price_id: str
    plan_id: str
    quantity: int = 1
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PortalRequest(BaseModel):
    organization_id: int
    return_url: Optional[str] = None


class CancelSubscriptionRequest(BaseModel):
    organization_id: int
    cancel_at_period_end: bool = True


def require_billing_admin(db: Session, user: User, organization_id: int):
    """Enforces that the caller has owner or billing_admin privileges."""
    if user.is_superuser:
        return
    membership = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == user.id,
            UserOrganization.organization_id == organization_id,
            UserOrganization.is_suspended.is_(False),
        )
        .first()
    )
    if not membership or membership.role not in (OrganizationRole.owner, OrganizationRole.billing_admin):
        raise AuthorizationError("Caller lacks billing administrator privileges for this organization")


def record_billing_audit_event(
    db: Session,
    action: str,
    actor_id: Optional[int],
    organization_id: int,
    details: Dict[str, Any],
):
    """Appends an immutable audit event for billing transactions."""
    event = AuditEvent(
        action=action,
        actor_id=actor_id,
        organization_id=organization_id,
        details=details,
    )
    db.add(event)
    db.commit()


@router.post("/checkout")
def create_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Dict[str, str]:
    require_billing_admin(db, current_user, payload.organization_id)
    result = billing_service.create_checkout_session(
        session=db,
        organization_id=payload.organization_id,
        email=current_user.email,
        price_id=payload.price_id,
        plan_id=payload.plan_id,
        quantity=payload.quantity,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    record_billing_audit_event(
        db,
        action="billing.checkout_session_created",
        actor_id=current_user.id,
        organization_id=payload.organization_id,
        details={"plan_id": payload.plan_id, "session_id": result.get("id")},
    )
    return result


@router.post("/portal")
def create_customer_portal(
    payload: PortalRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Dict[str, str]:
    require_billing_admin(db, current_user, payload.organization_id)
    result = billing_service.create_billing_portal_session(
        session=db,
        organization_id=payload.organization_id,
        return_url=payload.return_url,
    )
    record_billing_audit_event(
        db,
        action="billing.portal_session_created",
        actor_id=current_user.id,
        organization_id=payload.organization_id,
        details={"return_url": payload.return_url},
    )
    return result


@router.get("/subscription")
def get_subscription(
    organization_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    require_billing_admin(db, current_user, organization_id)
    sub = billing_service.get_active_subscription(db, organization_id)
    record_billing_audit_event(
        db,
        action="billing.subscription_viewed",
        actor_id=current_user.id,
        organization_id=organization_id,
        details={"has_active_subscription": sub is not None},
    )
    if not sub:
        return {"status": "none", "subscription": None}
    return {
        "status": sub.status,
        "subscription": {
            "id": sub.stripe_subscription_id,
            "plan_id": sub.plan_id,
            "status": sub.status,
            "quantity": sub.quantity,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        },
    }


@router.post("/subscription/cancel")
def cancel_subscription(
    payload: CancelSubscriptionRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    require_billing_admin(db, current_user, payload.organization_id)
    sub = billing_service.cancel_subscription(
        session=db,
        organization_id=payload.organization_id,
        cancel_at_period_end=payload.cancel_at_period_end,
    )
    record_billing_audit_event(
        db,
        action="billing.subscription_cancelled",
        actor_id=current_user.id,
        organization_id=payload.organization_id,
        details={
            "subscription_id": sub.stripe_subscription_id,
            "cancel_at_period_end": payload.cancel_at_period_end,
        },
    )
    return {
        "status": sub.status,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "canceled_at": sub.canceled_at.isoformat() if sub.canceled_at else None,
    }


@router.get("/invoices")
def list_invoices(
    organization_id: int,
    limit: int = 10,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> List[Dict[str, Any]]:
    require_billing_admin(db, current_user, organization_id)
    invoices = billing_service.list_invoices(db, organization_id, limit=limit)
    record_billing_audit_event(
        db,
        action="billing.invoices_viewed",
        actor_id=current_user.id,
        organization_id=organization_id,
        details={"count": len(invoices)},
    )
    return [
        {
            "id": inv.stripe_invoice_id,
            "amount_due": inv.amount_due,
            "amount_paid": inv.amount_paid,
            "currency": inv.currency,
            "status": inv.status,
            "hosted_invoice_url": inv.hosted_invoice_url,
            "invoice_pdf": inv.invoice_pdf,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invoices
    ]


@router.get("/usage")
def get_usage(
    organization_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    require_billing_admin(db, current_user, organization_id)
    summary = UsageMeteringService.get_metered_summary(db, organization_id)
    record_billing_audit_event(
        db,
        action="billing.usage_queried",
        actor_id=current_user.id,
        organization_id=organization_id,
        details={},
    )
    return summary


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    body_bytes = await request.body()
    try:
        event = billing_service.verify_webhook_signature(body_bytes, stripe_signature)
    except AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return billing_service.handle_webhook_event(db, event)
