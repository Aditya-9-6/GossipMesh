"""
Subscription Plan Enforcement Service (Task 89).

Implements Free Trial, Free, Team, Business, and Enterprise plans with seats,
repositories, monthly usage limits, feature flags, overages, and grace periods.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Set
from sqlalchemy import select
from sqlalchemy.orm import Session

from gossipmesh.billing.usage_metering import MetricType, UsageMeteringService
from gossipmesh.core.exceptions import (
    FeatureNotAvailableInPlanError,
    PlanLimitExceededError,
    ValidationError,
)
from gossipmesh.models.billing import BillingSubscription
from gossipmesh.models.organization import Organization


class PlanType(str, Enum):
    FREE = "free"
    FREE_TRIAL = "free_trial"
    TEAM = "team"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


@dataclass(frozen=True)
class PlanDefinition:
    plan_type: PlanType
    name: str
    max_seats: int
    max_repositories: int
    monthly_prs: int
    monthly_tokens: int
    feature_flags: Set[str]
    allow_overages: bool
    grace_period_days: int


PLAN_REGISTRY: Dict[PlanType, PlanDefinition] = {
    PlanType.FREE: PlanDefinition(
        plan_type=PlanType.FREE,
        name="Free",
        max_seats=1,
        max_repositories=1,
        monthly_prs=50,
        monthly_tokens=500_000,
        feature_flags={"basic_scan", "github_integration"},
        allow_overages=False,
        grace_period_days=0,
    ),
    PlanType.FREE_TRIAL: PlanDefinition(
        plan_type=PlanType.FREE_TRIAL,
        name="14-Day Free Trial",
        max_seats=5,
        max_repositories=3,
        monthly_prs=200,
        monthly_tokens=2_000_000,
        feature_flags={"basic_scan", "github_integration", "premium_scanners", "vector_search"},
        allow_overages=False,
        grace_period_days=3,
    ),
    PlanType.TEAM: PlanDefinition(
        plan_type=PlanType.TEAM,
        name="Team",
        max_seats=10,
        max_repositories=10,
        monthly_prs=500,
        monthly_tokens=10_000_000,
        feature_flags={"basic_scan", "github_integration", "premium_scanners", "vector_search", "slack_notifications"},
        allow_overages=True,
        grace_period_days=7,
    ),
    PlanType.BUSINESS: PlanDefinition(
        plan_type=PlanType.BUSINESS,
        name="Business",
        max_seats=50,
        max_repositories=50,
        monthly_prs=2_500,
        monthly_tokens=50_000_000,
        feature_flags={
            "basic_scan",
            "github_integration",
            "premium_scanners",
            "vector_search",
            "slack_notifications",
            "sso_saml",
            "scim_provisioning",
            "audit_export",
        },
        allow_overages=True,
        grace_period_days=14,
    ),
    PlanType.ENTERPRISE: PlanDefinition(
        plan_type=PlanType.ENTERPRISE,
        name="Enterprise",
        max_seats=10_000,
        max_repositories=10_000,
        monthly_prs=1_000_000,
        monthly_tokens=1_000_000_000,
        feature_flags={
            "basic_scan",
            "github_integration",
            "premium_scanners",
            "vector_search",
            "slack_notifications",
            "sso_saml",
            "scim_provisioning",
            "audit_export",
            "custom_sandbox_rules",
            "dedicated_workers",
            "sla_guarantee",
        },
        allow_overages=True,
        grace_period_days=30,
    ),
}


class PlanEnforcementService:
    """Enforces subscription plan quotas, feature gates, seats, and grace periods."""

    @staticmethod
    def get_organization_plan(session: Session, organization_id: int) -> PlanDefinition:
        """Determines the active PlanDefinition for an organization."""
        stmt = (
            select(BillingSubscription)
            .where(BillingSubscription.organization_id == organization_id)
            .order_by(BillingSubscription.created_at.desc())
        )
        sub = session.execute(stmt).scalars().first()

        if not sub:
            return PLAN_REGISTRY[PlanType.FREE]

        try:
            ptype = PlanType(sub.plan_id.lower())
        except ValueError:
            ptype = PlanType.FREE

        plan_def = PLAN_REGISTRY.get(ptype, PLAN_REGISTRY[PlanType.FREE])

        # Check status and past_due grace period
        if sub.status == "past_due":
            # Grace period calculation
            period_end = sub.current_period_end or sub.created_at
            now_dt = datetime.now(timezone.utc)
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)

            grace_deadline = period_end + timedelta(days=plan_def.grace_period_days)
            if now_dt > grace_deadline:
                raise PlanLimitExceededError(
                    f"Organization {organization_id} subscription is past due and grace period "
                    f"({plan_def.grace_period_days} days) expired on {grace_deadline.isoformat()}."
                )

        elif sub.status == "canceled":
            return PLAN_REGISTRY[PlanType.FREE]

        return plan_def

    @staticmethod
    def enforce_seat_allocation(session: Session, organization_id: int, total_seats_requested: int) -> None:
        """Ensures total allocated seats do not exceed plan maximum."""
        plan = PlanEnforcementService.get_organization_plan(session, organization_id)
        if total_seats_requested > plan.max_seats:
            raise PlanLimitExceededError(
                f"Seat allocation ({total_seats_requested}) exceeds plan '{plan.name}' limit of {plan.max_seats} seats"
            )

    @staticmethod
    def enforce_repository_limit(session: Session, organization_id: int, total_repos_requested: int) -> None:
        """Ensures repository count does not exceed plan maximum."""
        plan = PlanEnforcementService.get_organization_plan(session, organization_id)
        if total_repos_requested > plan.max_repositories:
            raise PlanLimitExceededError(
                f"Repository count ({total_repos_requested}) exceeds plan '{plan.name}' limit of {plan.max_repositories} repositories"
            )

    @staticmethod
    def enforce_usage_quota(
        session: Session,
        organization_id: int,
        metric: MetricType | str,
        increment: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Enforces monthly usage ceilings (PR reviews, tokens).
        Allows overages if configured on the plan.
        """
        plan = PlanEnforcementService.get_organization_plan(session, organization_id)
        metric_str = metric.value if isinstance(metric, MetricType) else str(metric)

        totals = UsageMeteringService.aggregate_usage(session, organization_id)
        current_used = totals.get(metric_str, 0.0)
        projected = current_used + increment

        limit = plan.monthly_prs if metric_str == MetricType.REVIEWED_PRS.value else plan.monthly_tokens
        if projected > limit:
            if not plan.allow_overages:
                raise PlanLimitExceededError(
                    f"Usage limit exceeded for {metric_str}: requested {projected}, limit is {limit} on plan '{plan.name}'"
                )
            return {
                "status": "overage_permitted",
                "current_used": current_used,
                "projected": projected,
                "limit": limit,
                "overage": projected - limit,
            }

        return {
            "status": "within_limit",
            "current_used": current_used,
            "projected": projected,
            "limit": limit,
        }

    @staticmethod
    def enforce_feature_flag(session: Session, organization_id: int, feature_flag: str) -> None:
        """Verifies that an enterprise feature flag is enabled for the organization's plan."""
        plan = PlanEnforcementService.get_organization_plan(session, organization_id)
        if feature_flag not in plan.feature_flags:
            raise FeatureNotAvailableInPlanError(
                f"Feature '{feature_flag}' is not available on plan '{plan.name}'. Please upgrade to access this feature."
            )
