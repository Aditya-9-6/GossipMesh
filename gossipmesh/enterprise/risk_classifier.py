import re
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ChangeDetails(BaseModel):
    files_changed: List[str] = Field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    has_migrations: bool = False
    has_dependencies_change: bool = False
    has_auth_change: bool = False
    has_infrastructure_change: bool = False
    has_shell_scripts: bool = False
    has_security_code: bool = False
    has_tests: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RiskEvaluationResult(BaseModel):
    risk_level: RiskLevel
    requires_approval: bool
    blocked: bool
    reasons: List[str] = Field(default_factory=list)

class ChangeRiskClassifier:
    SENSITIVE_DIRS = [
        "gossipmesh/auth/",
        "gossipmesh/core/security",
        "alembic/",
        "scripts/security/"
    ]
    INFRA_EXTS = [".tf", ".yaml", ".yml", "Dockerfile", "docker-compose.yml"]

    def __init__(self):
        pass

    def classify(self, change: ChangeDetails) -> RiskEvaluationResult:
        reasons = []
        total_files = len(change.files_changed)
        total_lines = change.additions + change.deletions

        # Check sensitive directories
        sensitive_file_hits = 0
        for f in change.files_changed:
            for sdir in self.SENSITIVE_DIRS:
                if sdir in f:
                    sensitive_file_hits += 1
                    reasons.append(f"Touches sensitive path: {f}")

        # Check file types / extensions
        infra_hits = 0
        shell_hits = 0
        for f in change.files_changed:
            if any(f.endswith(ext) or ext in f for ext in self.INFRA_EXTS):
                infra_hits += 1
            if f.endswith(".sh") or "bin/" in f:
                shell_hits += 1

        if change.has_infrastructure_change or infra_hits > 0:
            reasons.append("Modifies infrastructure or deployment configurations.")

        if change.has_shell_scripts or shell_hits > 0:
            reasons.append("Contains shell scripts or executable batch scripts.")

        if change.has_auth_change:
            reasons.append("Modifies core authentication or authorization logic.")

        if change.has_migrations:
            reasons.append("Includes database migrations.")

        if change.has_dependencies_change:
            reasons.append("Updates project dependencies or requirements.")

        if change.has_security_code:
            reasons.append("Modifies security or cryptographic primitives.")

        # Line and file thresholds
        if total_files > 50 or total_lines > 2000:
            reasons.append(f"Extremely large changeset: {total_files} files, {total_lines} lines changed.")
            risk = RiskLevel.CRITICAL
        elif change.has_auth_change and total_lines > 500:
            reasons.append("Large authentication modification detected.")
            risk = RiskLevel.CRITICAL
        elif sensitive_file_hits > 3 and change.has_migrations:
            reasons.append("Multiple sensitive files combined with schema migrations.")
            risk = RiskLevel.CRITICAL
        elif total_files > 20 or total_lines > 500 or sensitive_file_hits > 0 or change.has_auth_change or change.has_migrations or change.has_infrastructure_change:
            if total_files > 25 or total_lines > 1000:
                risk = RiskLevel.HIGH
            else:
                risk = RiskLevel.MEDIUM
                if not reasons:
                    reasons.append("Moderate file or line count changes.")
        else:
            risk = RiskLevel.LOW
            reasons.append("Small, low-risk changeset.")

        # Override to CRITICAL if extreme risk conditions met
        if risk == RiskLevel.CRITICAL:
            return RiskEvaluationResult(
                risk_level=RiskLevel.CRITICAL,
                requires_approval=True,
                blocked=True,
                reasons=reasons
            )

        requires_approval = risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)
        blocked = False

        return RiskEvaluationResult(
            risk_level=risk,
            requires_approval=requires_approval,
            blocked=blocked,
            reasons=reasons
        )
