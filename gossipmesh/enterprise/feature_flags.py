"""
Organization-Scoped Feature Flags & Emergency Kill Switch Engine (Task 124).

Supports flags for:
- autonomous_review
- security_scanning
- ast_indexing
- issue_solving
- ci_fixing
- patch_generation
- strict_sandboxing
- beta_providers

Provides global emergency kill-switch and organization-level override controls.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Set
from sqlalchemy.orm import Session

from gossipmesh.models.audit import AuditEvent


class FeatureFlagKey(str, Enum):
    AUTONOMOUS_REVIEW = "autonomous_review"
    SECURITY_SCANNING = "security_scanning"
    AST_INDEXING = "ast_indexing"
    ISSUE_SOLVING = "issue_solving"
    CI_FIXING = "ci_fixing"
    PATCH_GENERATION = "patch_generation"
    STRICT_SANDBOXING = "strict_sandboxing"
    BETA_PROVIDERS = "beta_providers"


# Safe default states
DEFAULT_FLAG_STATES: Dict[FeatureFlagKey, bool] = {
    FeatureFlagKey.AUTONOMOUS_REVIEW: True,
    FeatureFlagKey.SECURITY_SCANNING: True,
    FeatureFlagKey.AST_INDEXING: True,
    FeatureFlagKey.ISSUE_SOLVING: True,
    FeatureFlagKey.CI_FIXING: True,
    FeatureFlagKey.PATCH_GENERATION: True,
    FeatureFlagKey.STRICT_SANDBOXING: True,
    FeatureFlagKey.BETA_PROVIDERS: False,
}


class FeatureFlagService:
    """Manages organization-scoped feature toggles and global emergency kill switches."""

    def __init__(self):
        self._global_emergency_disabled: Set[str] = set()
        self._org_overrides: Dict[int, Dict[str, bool]] = {}

    def emergency_disable_globally(
        self,
        session: Session,
        flag: FeatureFlagKey | str,
        actor_id: Optional[int] = None,
        reason: str = "Emergency kill switch activated",
    ) -> None:
        """Globally disables a feature across ALL tenants immediately."""
        flag_str = flag.value if isinstance(flag, FeatureFlagKey) else str(flag)
        self._global_emergency_disabled.add(flag_str)

        audit = AuditEvent(
            action="feature_flag.emergency_disabled",
            actor_id=actor_id,
            details={"flag": flag_str, "reason": reason},
        )
        session.add(audit)
        session.commit()

    def lift_global_emergency_disable(self, flag: FeatureFlagKey | str) -> None:
        """Restores feature from global emergency kill switch."""
        flag_str = flag.value if isinstance(flag, FeatureFlagKey) else str(flag)
        self._global_emergency_disabled.discard(flag_str)

    def set_organization_flag(
        self,
        session: Session,
        organization_id: int,
        flag: FeatureFlagKey | str,
        enabled: bool,
        actor_id: Optional[int] = None,
    ) -> None:
        """Sets an organization-specific flag override."""
        flag_str = flag.value if isinstance(flag, FeatureFlagKey) else str(flag)
        if organization_id not in self._org_overrides:
            self._org_overrides[organization_id] = {}
        self._org_overrides[organization_id][flag_str] = enabled

        audit = AuditEvent(
            action="feature_flag.org_override_set",
            actor_id=actor_id,
            organization_id=organization_id,
            details={"flag": flag_str, "enabled": enabled},
        )
        session.add(audit)
        session.commit()

    def is_enabled(
        self,
        organization_id: int,
        flag: FeatureFlagKey | str,
    ) -> bool:
        """
        Evaluates whether a feature is active for an organization.
        Enforces global emergency kill switch with top priority.
        """
        flag_str = flag.value if isinstance(flag, FeatureFlagKey) else str(flag)

        # 1. Global emergency kill switch overrides all
        if flag_str in self._global_emergency_disabled:
            return False

        # 2. Organization-specific override
        org_flags = self._org_overrides.get(organization_id, {})
        if flag_str in org_flags:
            return org_flags[flag_str]

        # 3. Default state
        try:
            enum_key = FeatureFlagKey(flag_str)
            return DEFAULT_FLAG_STATES.get(enum_key, False)
        except ValueError:
            return False
