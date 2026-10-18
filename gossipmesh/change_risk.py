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
    has_auth_changes: bool = False
    has_migrations: bool = False
    has_dependency_updates: bool = False
    has_infrastructure_changes: bool = False
    has_shell_scripts: bool = False
    has_security_code: bool = False
    has_test_changes: bool = False
    sensitive_dirs: List[str] = Field(default_factory=lambda: ["auth", "security", "crypto", "iam", "secrets"])

class ChangeRiskAssessment(BaseModel):
    risk_level: RiskLevel
    requires_approval: bool
    is_blocked: bool
    reasons: List[str] = Field(default_factory=list)
    score: int = 0

class ChangeRiskClassifier:
    def __init__(self, max_allowed_risk: RiskLevel = RiskLevel.HIGH):
        self.max_allowed_risk = max_allowed_risk
        self.risk_hierarchy = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4
        }

    def classify(self, details: ChangeDetails) -> ChangeRiskAssessment:
        reasons = []
        score = 0

        # Check sensitive directories in files changed
        in_sensitive_dir = False
        for f in details.files_changed:
            for sdir in details.sensitive_dirs:
                if sdir in f.lower() or f.startswith(sdir):
                    in_sensitive_dir = True
                    break

        # Critical triggers
        is_critical = False
        if details.file_count > 50 or details.line_count > 2000:
            is_critical = True
            reasons.append(f"Massive change footprint: {details.file_count} files, {details.line_count} lines.")

        if details.has_security_code and (details.has_auth_changes or in_sensitive_dir):
            is_critical = True
            reasons.append("Critical security and authentication code modifications detected.")

        if is_critical:
            return ChangeRiskAssessment(
                risk_level=RiskLevel.CRITICAL,
                requires_approval=True,
                is_blocked=True,
                reasons=reasons,
                score=100
            )

        # High triggers
        is_high = False
        if details.has_auth_changes:
            is_high = True
            reasons.append("Authentication logic changes detected.")
        if details.has_migrations:
            is_high = True
            reasons.append("Database migration changes detected.")
        if details.has_infrastructure_changes:
            is_high = True
            reasons.append("Infrastructure or IaC configuration changes detected.")
        if in_sensitive_dir:
            is_high = True
            reasons.append("Changes within sensitive system directories detected.")
        if details.file_count > 15 or details.line_count > 500:
            is_high = True
            reasons.append(f"Large change footprint: {details.file_count} files, {details.line_count} lines.")

        if is_high:
            return ChangeRiskAssessment(
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                is_blocked=self.risk_hierarchy[RiskLevel.HIGH] > self.risk_hierarchy[self.max_allowed_risk],
                reasons=reasons,
                score=75
            )

        # Medium triggers
        is_medium = False
        if details.has_dependency_updates:
            is_medium = True
            reasons.append("External dependency updates detected.")
        if details.has_shell_scripts:
            is_medium = True
            reasons.append("Shell script modifications detected.")
        if details.file_count > 5 or details.line_count > 100:
            is_medium = True
            reasons.append(f"Moderate change footprint: {details.file_count} files, {details.line_count} lines.")

        if is_medium:
            return ChangeRiskAssessment(
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                is_blocked=self.risk_hierarchy[RiskLevel.MEDIUM] > self.risk_hierarchy[self.max_allowed_risk],
                reasons=reasons,
                score=40
            );

        # Low default
        reasons.append("Standard low-risk change.")
        return ChangeRiskAssessment(
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            is_blocked=False,
            reasons=reasons,
            score=10
        )
