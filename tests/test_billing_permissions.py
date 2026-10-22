import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, OrganizationRole, UserOrganization
from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.billing import BillingSubscription
from gossipmesh.billing.stripe_service import StripeBillingService
from gossipmesh.api.routers.billing import (
    require_billing_admin,
    create_checkout,
    create_customer_portal,
    cancel_subscription,
    list_invoices,
    get_usage,
    CheckoutRequest,
    PortalRequest,
    CancelSubscriptionRequest,
)
from gossipmesh.core.exceptions import AuthorizationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="SecureCorp")
    session.add(org)

    # Users
    owner = User(id=1, email="owner@corp.com", hashed_password="pw", is_active=True, is_superuser=False)
    billing_admin = User(id=2, email="billing@corp.com", hashed_password="pw", is_active=True, is_superuser=False)
    developer = User(id=3, email="dev@corp.com", hashed_password="pw", is_active=True, is_superuser=False)
    suspended_admin = User(id=4, email="suspended@corp.com", hashed_password="pw", is_active=True, is_superuser=False)
    superuser = User(id=5, email="root@corp.com", hashed_password="pw", is_active=True, is_superuser=True)

    session.add_all([owner, billing_admin, developer, suspended_admin, superuser])
    session.commit()

    # Memberships
    m_owner = UserOrganization(user_id=1, organization_id=1, role=OrganizationRole.owner)
    m_admin = UserOrganization(user_id=2, organization_id=1, role=OrganizationRole.billing_admin)
    m_dev = UserOrganization(user_id=3, organization_id=1, role=OrganizationRole.developer)
    m_susp = UserOrganization(user_id=4, organization_id=1, role=OrganizationRole.billing_admin, is_suspended=True)

    session.add_all([m_owner, m_admin, m_dev, m_susp])
    session.commit()

    yield session
    session.close()


def test_billing_rbac_matrix(db_session):
    owner = db_session.get(User, 1)
    admin = db_session.get(User, 2)
    dev = db_session.get(User, 3)
    suspended = db_session.get(User, 4)
    root = db_session.get(User, 5)

    # Owner, Admin, Superuser allowed
    require_billing_admin(db_session, owner, 1)
    require_billing_admin(db_session, admin, 1)
    require_billing_admin(db_session, root, 1)

    # Developer blocked
    with pytest.raises(AuthorizationError) as exc_info:
        require_billing_admin(db_session, dev, 1)
    assert "lacks billing administrator privileges" in str(exc_info.value)

    # Suspended admin blocked
    with pytest.raises(AuthorizationError) as exc_info:
        require_billing_admin(db_session, suspended, 1)
    assert "lacks billing administrator privileges" in str(exc_info.value)


def test_billing_operations_emit_audit_trail(db_session):
    admin = db_session.get(User, 2)

    # 1. Checkout session
    checkout_res = create_checkout(
        payload=CheckoutRequest(
            organization_id=1,
            price_id="price_monthly",
            plan_id="team",
        ),
        current_user=admin,
        db=db_session,
    )
    assert "id" in checkout_res

    # 2. Portal session
    portal_res = create_customer_portal(
        payload=PortalRequest(organization_id=1),
        current_user=admin,
        db=db_session,
    )
    assert "url" in portal_res

    # 3. List invoices
    invoices = list_invoices(organization_id=1, current_user=admin, db=db_session)
    assert isinstance(invoices, list)

    # 4. Get usage
    usage = get_usage(organization_id=1, current_user=admin, db=db_session)
    assert "metrics" in usage

    # Verify audit events emitted
    events = db_session.query(AuditEvent).filter(AuditEvent.organization_id == 1).all()
    actions = {e.action for e in events}
    assert "billing.checkout_session_created" in actions
    assert "billing.portal_session_created" in actions
    assert "billing.invoices_viewed" in actions
    assert "billing.usage_queried" in actions

    # Every event records actor_id 2
    for e in events:
        assert e.actor_id == 2
