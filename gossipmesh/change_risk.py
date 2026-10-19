import re
from enum import Enum
from typing import List, Dict, Any, Set, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ChangeDetails(BaseModel):
    file_count: int = 0
    line_count: int = 0
    files_changed: List[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    diff_content: str = ""
    has_auth_changes: bool = False
    has_migrations: bool = False
    has_dependency_updates: bool = False
    has_infrastructure_changes: bool = False
    has_shell_scripts: bool = False
    has_security_code: bool = False
    has_test_changes: bool = False
    has_tests: bool = False
    has_dependency_changes: bool = False
    has_infra_changes: bool = False
    sensitive_dirs: List[str] = Field(default_factory=lambda: ["auth", "security", "crypto", "iam", "secrets"])


class ChangeRiskAssessment(BaseModel):
    risk_level: RiskLevel
    requires_approval: bool
    is_blocked: bool = False
    blocked: bool = False
    reasons: List[str] = Field(default_factory=list)
    score: int = 0


class ChangeRiskClassifier:
    def __init__(self, max_allowed_risk: RiskLevel = RiskLevel.HIGH):
        self.max_allowed_risk = max_allowed_risk
        self.risk_hierarchy = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}

    def classify(self, details: ChangeDetails) -> ChangeRiskAssessment:
        reasons = []
        score = 0

        # Support both flag naming variants
        has_dep = details.has_dependency_updates or details.has_dependency_changes
        has_infra = details.has_infrastructure_changes or details.has_infra_changes
        total_lines = details.line_count or (details.insertions + details.deletions)
        total_files = details.file_count or len(details.files_changed)

        # Check sensitive directories in files changed
        in_sensitive_dir = False
        for f in details.files_changed:
            for sdir in details.sensitive_dirs:
                if sdir in f.lower() or f.startswith(sdir):
                    in_sensitive_dir = True
                    break

        # Critical triggers
        is_critical = False
        if total_files > 50 or total_lines > 2000:
            is_critical = True
            reasons.append(f"Massive change footprint: {total_files} files, {total_lines} lines.")

        if details.has_security_code and (details.has_auth_changes or in_sensitive_dir):
            is_critical = True
            reasons.append("Critical security and authentication code modifications detected.")

        if is_critical:
            return ChangeRiskAssessment(
                risk_level=RiskLevel.CRITICAL,
                requires_approval=True,
                is_blocked=True,
                blocked=True,
                reasons=reasons,
                score=100,
            )

        # High triggers
        is_high = False
        if details.has_auth_changes:
            is_high = True
            reasons.append("Authentication logic changes detected.")
        if details.has_migrations:
            is_high = True
            reasons.append("Database migration changes detected.")
        if has_infra:
            is_high = True
            reasons.append("Infrastructure or IaC configuration changes detected.")
        if in_sensitive_dir:
            is_high = True
            reasons.append("Changes within sensitive system directories detected.")
        if total_files > 15 or total_lines > 500:
            is_high = True
            reasons.append(f"Large change footprint: {total_files} files, {total_lines} lines.")

        if is_high:
            blocked_val = self.risk_hierarchy[RiskLevel.HIGH] > self.risk_hierarchy[self.max_allowed_risk]
            return ChangeRiskAssessment(
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                is_blocked=blocked_val,
                blocked=blocked_val,
                reasons=reasons,
                score=75,
            )

        # Medium triggers
        is_medium = False
        if has_dep:
            is_medium = True
            reasons.append("External dependency updates detected.")
        if details.has_shell_scripts:
            is_medium = True
            reasons.append("Shell script modifications detected.")
        if total_files > 5 or total_lines > 100:
            is_medium = True
            reasons.append(f"Moderate change footprint: {total_files} files, {total_lines} lines.")

        if is_medium:
            blocked_val = self.risk_hierarchy[RiskLevel.MEDIUM] > self.risk_hierarchy[self.max_allowed_risk]
            return ChangeRiskAssessment(
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                is_blocked=blocked_val,
                blocked=blocked_val,
                reasons=reasons,
                score=40,
            )

        # Low default
        reasons.append("Standard low-risk change.")
        return ChangeRiskAssessment(
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            is_blocked=False,
            blocked=False,
            reasons=reasons,
            score=10,
        )
