from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.billing import BillingSubscription
from gossipmesh.billing.plan_enforcement import (
    PlanEnforcementService,
    PlanType,
    PLAN_REGISTRY,
)
from gossipmesh.billing.usage_metering import MetricType, UsageMeteringService
from gossipmesh.core.exceptions import (
    FeatureNotAvailableInPlanError,
    PlanLimitExceededError,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="AcmeTech")
    session.add(org)
    session.commit()

    yield session
    session.close()


def test_free_plan_defaults_and_limits(db_session):
    # No subscription -> defaults to FREE plan
    plan = PlanEnforcementService.get_organization_plan(db_session, 1)
    assert plan.plan_type == PlanType.FREE
    assert plan.max_seats == 1
    assert plan.max_repositories == 1
    assert plan.monthly_prs == 50
    assert plan.allow_overages is False

    # 1 seat allowed, 2 seats rejected
    PlanEnforcementService.enforce_seat_allocation(db_session, 1, 1)
    with pytest.raises(PlanLimitExceededError) as exc_info:
        PlanEnforcementService.enforce_seat_allocation(db_session, 1, 2)
    assert "exceeds plan 'Free' limit of 1 seats" in str(exc_info.value)

    # 1 repo allowed, 2 repos rejected
    PlanEnforcementService.enforce_repository_limit(db_session, 1, 1)
    with pytest.raises(PlanLimitExceededError) as exc_info:
        PlanEnforcementService.enforce_repository_limit(db_session, 1, 2)
    assert "exceeds plan 'Free' limit of 1 repositories" in str(exc_info.value)


def test_feature_flag_gating(db_session):
    # Free plan has basic_scan, but lacks sso_saml
    PlanEnforcementService.enforce_feature_flag(db_session, 1, "basic_scan")

    with pytest.raises(FeatureNotAvailableInPlanError) as exc_info:
        PlanEnforcementService.enforce_feature_flag(db_session, 1, "sso_saml")
    assert "not available on plan 'Free'" in str(exc_info.value)

    # Upgrade to Business plan
    sub = BillingSubscription(
        organization_id=1,
        stripe_subscription_id="sub_biz_1",
        stripe_customer_id="cus_1",
        plan_id="business",
        status="active",
    )
    db_session.add(sub)
    db_session.commit()

    # Now sso_saml and scim_provisioning are allowed
    PlanEnforcementService.enforce_feature_flag(db_session, 1, "sso_saml")
    PlanEnforcementService.enforce_feature_flag(db_session, 1, "scim_provisioning")

    # custom_sandbox_rules is Enterprise only
    with pytest.raises(FeatureNotAvailableInPlanError):
        PlanEnforcementService.enforce_feature_flag(db_session, 1, "custom_sandbox_rules")


def test_usage_quota_and_overage_handling(db_session):
    # Free plan overage rejected
    with pytest.raises(PlanLimitExceededError):
        PlanEnforcementService.enforce_usage_quota(
            db_session,
            organization_id=1,
            metric=MetricType.REVIEWED_PRS,
            increment=51.0,  # Limit is 50
        )

    # Upgrade to Team plan (allows overages)
    sub = BillingSubscription(
        organization_id=1,
        stripe_subscription_id="sub_team_1",
        stripe_customer_id="cus_1",
        plan_id="team",
        status="active",
    )
    db_session.add(sub)
    db_session.commit()

    # Exceed limit on Team plan returns overage_permitted
    res = PlanEnforcementService.enforce_usage_quota(
        db_session,
        organization_id=1,
        metric=MetricType.REVIEWED_PRS,
        increment=550.0,  # Team limit is 500
    )
    assert res["status"] == "overage_permitted"
    assert res["overage"] == 50.0


def test_past_due_grace_period_enforcement(db_session):
    now = datetime.now(timezone.utc)
    # Subscription expired 10 days ago with a 7-day grace period
    past_due_date = now - timedelta(days=10)
    sub = BillingSubscription(
        organization_id=1,
        stripe_subscription_id="sub_past_due",
        stripe_customer_id="cus_1",
        plan_id="team",
        status="past_due",
        current_period_end=past_due_date,
    )
    db_session.add(sub)
    db_session.commit()

    # Grace period expired -> raises PlanLimitExceededError
    with pytest.raises(PlanLimitExceededError) as exc_info:
        PlanEnforcementService.get_organization_plan(db_session, 1)
    assert "grace period (7 days) expired" in str(exc_info.value)
