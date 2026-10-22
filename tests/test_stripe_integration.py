import hashlib
import hmac
import time
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, OrganizationRole, UserOrganization
from gossipmesh.models.billing import (
    StripeCustomer,
    BillingSubscription,
    BillingInvoice,
    ProcessedWebhookEvent,
)
from gossipmesh.billing.stripe_service import StripeBillingService
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError, ValidationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(id=1, email="admin@test.com", hashed_password="pw", is_active=True, is_superuser=False)
    org = Organization(id=1, name="AcmeCorp")
    user_org = UserOrganization(user_id=1, organization_id=1, role=OrganizationRole.billing_admin)

    session.add(user)
    session.add(org)
    session.add(user_org)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def billing_service():
    return StripeBillingService(
        api_key="sk_test_dummy_mock_key",
        webhook_secret="whsec_test_secret_12345",
        test_mode=True,
    )


def test_customer_creation_and_retrieval(db_session, billing_service):
    # Customer doesn't exist initially
    assert billing_service.get_customer_by_org(db_session, 1) is None

    # Create customer
    customer = billing_service.get_or_create_customer(
        db_session,
        organization_id=1,
        email="admin@test.com",
        name="Acme Corp Billing",
    )
    assert customer.id is not None
    assert customer.organization_id == 1
    assert customer.email == "admin@test.com"
    assert customer.stripe_customer_id.startswith("cus_test_")

    # Subsequent retrieval returns the same customer
    same_customer = billing_service.get_or_create_customer(
        db_session,
        organization_id=1,
        email="admin@test.com",
    )
    assert same_customer.id == customer.id
    assert same_customer.stripe_customer_id == customer.stripe_customer_id


def test_checkout_and_portal_sessions(db_session, billing_service):
    checkout = billing_service.create_checkout_session(
        db_session,
        organization_id=1,
        email="admin@test.com",
        price_id="price_team_monthly",
        plan_id="team",
    )
    assert "id" in checkout
    assert "url" in checkout
    assert "checkout.stripe.com" in checkout["url"]

    portal = billing_service.create_billing_portal_session(
        db_session,
        organization_id=1,
    )
    assert "url" in portal
    assert "billing.stripe.com" in portal["url"]


def test_webhook_hmac_signature_verification(billing_service):
    payload = json.dumps({"id": "evt_123", "type": "customer.subscription.created"}).encode("utf-8")
    now_ts = int(time.time())

    # Generate valid signature
    signed_payload = f"{now_ts}.".encode("utf-8") + payload
    valid_sig = hmac.new(
        b"whsec_test_secret_12345",
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    header = f"t={now_ts},v1={valid_sig}"
    event = billing_service.verify_webhook_signature(payload, header)
    assert event["id"] == "evt_123"

    # Expired timestamp (e.g. 10 minutes ago)
    old_ts = now_ts - 600
    old_signed = f"{old_ts}.".encode("utf-8") + payload
    old_sig = hmac.new(b"whsec_test_secret_12345", old_signed, hashlib.sha256).hexdigest()
    with pytest.raises(AuthenticationError) as exc_info:
        billing_service.verify_webhook_signature(payload, f"t={old_ts},v1={old_sig}")
    assert "expired" in str(exc_info.value)

    # Tampered signature
    with pytest.raises(AuthenticationError) as exc_info:
        billing_service.verify_webhook_signature(payload, f"t={now_ts},v1=bad_signature_value")
    assert "mismatch" in str(exc_info.value)


def test_idempotent_webhook_processing_lifecycle(db_session, billing_service):
    # Ensure customer exists first
    customer = billing_service.get_or_create_customer(db_session, 1, "admin@test.com")

    # 1. customer.subscription.created
    sub_event = {
        "id": "evt_sub_created_001",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_stripe_123",
                "customer": customer.stripe_customer_id,
                "plan": {"id": "team_plan"},
                "status": "active",
                "quantity": 5,
                "cancel_at_period_end": False,
            }
        },
    }

    res1 = billing_service.handle_webhook_event(db_session, sub_event)
    assert res1["status"] == "success"

    active_sub = billing_service.get_active_subscription(db_session, 1)
    assert active_sub is not None
    assert active_sub.stripe_subscription_id == "sub_stripe_123"
    assert active_sub.plan_id == "team_plan"
    assert active_sub.quantity == 5

    # 2. Idempotency check: replay identical event
    res1_duplicate = billing_service.handle_webhook_event(db_session, sub_event)
    assert res1_duplicate["status"] == "already_processed"

    # 3. customer.subscription.updated
    update_event = {
        "id": "evt_sub_updated_002",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe_123",
                "customer": customer.stripe_customer_id,
                "plan": {"id": "business_plan"},
                "status": "active",
                "quantity": 10,
                "cancel_at_period_end": True,
            }
        },
    }
    billing_service.handle_webhook_event(db_session, update_event)
    db_session.refresh(active_sub)
    assert active_sub.plan_id == "business_plan"
    assert active_sub.quantity == 10
    assert active_sub.cancel_at_period_end is True

    # 4. invoice.paid
    inv_event = {
        "id": "evt_inv_paid_003",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_stripe_456",
                "customer": customer.stripe_customer_id,
                "amount_due": 5000,
                "amount_paid": 5000,
                "currency": "usd",
                "status": "paid",
                "hosted_invoice_url": "https://invoice.stripe.com/456",
            }
        },
    }
    billing_service.handle_webhook_event(db_session, inv_event)
    invoices = billing_service.list_invoices(db_session, 1)
    assert len(invoices) == 1
    assert invoices[0].stripe_invoice_id == "in_stripe_456"
    assert invoices[0].amount_paid == 5000

    # 5. Cancel subscription via service
    canceled_sub = billing_service.cancel_subscription(db_session, 1, cancel_at_period_end=False)
    assert canceled_sub.status == "canceled"
    assert canceled_sub.canceled_at is not None
