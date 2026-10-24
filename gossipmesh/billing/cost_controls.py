"""
Enterprise Cost Controls & Anomaly Detection Engine (Task 92).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.organization import Organization
from gossipmesh.models.runtime import Budget, Job, Workflow


class BudgetAlertLevel(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"  # >= 80%
    EXCEEDED = "exceeded"  # >= 100%


@dataclass
class CostControlConfig:
    warning_threshold_ratio: float = 0.80
    critical_threshold_ratio: float = 1.00
    anomaly_multiplier: float = 3.0
    min_anomaly_threshold_usd: float = 10.0
    emergency_shutdown_enabled: bool = True


class CostControlsEngine:
    def __init__(self, config: Optional[CostControlConfig] = None):
        self.config = config or CostControlConfig()

    def check_organization_budget(
        self,
        session: Session,
        organization_id: int,
    ) -> Tuple[BudgetAlertLevel, Dict[str, Any]]:
        stmt = select(Budget).where(Budget.organization_id == organization_id)
        budget = session.execute(stmt).scalars().first()

        if not budget or budget.monthly_limit_usd <= 0:
            return BudgetAlertLevel.NORMAL, {
                "organization_id": organization_id,
                "current_spend_usd": budget.current_spend_usd if budget else 0.0,
                "monthly_limit_usd": budget.monthly_limit_usd if budget else 0.0,
                "ratio": 0.0,
            }

        ratio = budget.current_spend_usd / budget.monthly_limit_usd
        status = BudgetAlertLevel.NORMAL

        if ratio >= self.config.critical_threshold_ratio:
            status = BudgetAlertLevel.EXCEEDED
            action = "billing.budget_exceeded"
        elif ratio >= self.config.warning_threshold_ratio:
            status = BudgetAlertLevel.WARNING
            action = "billing.budget_warning"
        else:
            action = None

        details = {
            "organization_id": organization_id,
            "current_spend_usd": budget.current_spend_usd,
            "monthly_limit_usd": budget.monthly_limit_usd,
            "ratio": round(ratio, 4),
        }

        if action:
            audit = AuditEvent(
                action=action,
                organization_id=organization_id,
                details=details,
            )
            session.add(audit)
            session.commit()

        return status, details

    def detect_cost_anomaly(
        self,
        historical_spends: List[float],
        current_spend: float,
    ) -> Tuple[bool, str]:
        if not historical_spends or len(historical_spends) < 3:
            return False, "Insufficient historical data for anomaly baseline"

        valid_spends = [s for s in historical_spends if s >= 0]
        n = len(valid_spends)
        mean = sum(valid_spends) / n

        variance = sum((x - mean) ** 2 for x in valid_spends) / n
        std_dev = math.sqrt(variance)

        threshold = mean + (self.config.anomaly_multiplier * max(std_dev, 1.0))

        if current_spend > threshold and current_spend >= self.config.min_anomaly_threshold_usd:
            msg = (
                f"Cost anomaly detected: current spend (${current_spend:.2f}) exceeds baseline threshold "
                f"(${threshold:.2f}, mean=${mean:.2f}, std_dev=${std_dev:.2f})"
            )
            return True, msg

        return False, "Spend is within normal statistical distribution"

    def trigger_emergency_shutdown(
        self,
        session: Session,
        organization_id: int,
        reason: str,
        actor: str = "cost_controls_watchdog",
    ) -> int:
        """
        Immediately pauses and cancels all running and pending workflows and jobs
        for the given organization to prevent uncontrolled runaway spend.
        Emits high-severity audit record.
        """
        wf_stmt = (
            update(Workflow)
            .where(
                Workflow.organization_id == organization_id,
                Workflow.status.in_(["pending", "running"]),
            )
            .values(status="cancelled")
        )
        wf_result = session.execute(wf_stmt)
        session.commit()
        workflows_stopped = int(getattr(wf_result, "rowcount", 0) or 0)

        job_stmt = (
            update(Job)
            .where(
                Job.workflow_id.in_(select(Workflow.id).where(Workflow.organization_id == organization_id)),
                Job.status.in_(["pending", "running"]),
            )
            .values(status="cancelled")
        )
        session.execute(job_stmt)
        session.commit()

        audit = AuditEvent(
            action="billing.emergency_shutdown_triggered",
            organization_id=organization_id,
            details={
                "reason": reason,
                "actor": actor,
                "workflows_stopped": workflows_stopped,
            },
        )
        session.add(audit)
        session.commit()

        return 1

    def check_provider_cost_alert(
        self,
        provider_name: str,
        current_spend_usd: float,
        limit_usd: float,
    ) -> Optional[Dict[str, Any]]:
        if limit_usd <= 0:
            return None

        ratio = current_spend_usd / limit_usd
        if ratio >= self.config.critical_threshold_ratio:
            return {
                "provider": provider_name,
                "severity": "CRITICAL",
                "message": f"Provider {provider_name} has exceeded cost cap: ${current_spend_usd:.2f} / ${limit_usd:.2f}",
                "current_spend_usd": current_spend_usd,
                "limit_usd": limit_usd,
                "ratio": ratio,
            }
        elif ratio >= self.config.warning_threshold_ratio:
            return {
                "provider": provider_name,
                "severity": "WARNING",
                "message": f"Provider {provider_name} spend warning: ${current_spend_usd:.2f} is at {ratio * 100:.1f}% of cap",
                "current_spend_usd": current_spend_usd,
                "limit_usd": limit_usd,
                "ratio": ratio,
            }

        return None
