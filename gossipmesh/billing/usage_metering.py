"""
Durable Usage Metering Service (Task 88).

Meters reviewed PRs, changed lines, tokens, indexing operations, sandbox minutes,
seats, storage, and premium scanners with immutable, idempotent ledger records.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import ValidationError
from gossipmesh.models.billing import UsageRecord
from gossipmesh.models.organization import Organization


class MetricType(str, Enum):
    REVIEWED_PRS = "reviewed_prs"
    CHANGED_LINES = "changed_lines"
    AI_TOKENS = "ai_tokens"
    INDEXING_OPERATIONS = "indexing_operations"
    SANDBOX_MINUTES = "sandbox_minutes"
    SEATS = "seats"
    STORAGE_BYTES = "storage_bytes"
    PREMIUM_SCANNERS = "premium_scanners"


class UsageMeteringService:
    """Manages immutable, idempotent metered billing records."""

    @staticmethod
    def record_usage(
        session: Session,
        organization_id: int,
        metric_type: MetricType | str,
        quantity: float,
        idempotency_key: str,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """
        Records a metered consumption event idempotently.
        If idempotency_key is already present, returns the existing record.
        """
        if quantity < 0:
            raise ValidationError(f"Usage quantity cannot be negative: {quantity}")

        if not idempotency_key or not idempotency_key.strip():
            raise ValidationError("Usage record requires a non-empty idempotency_key")

        # Metric type validation
        m_type = metric_type.value if isinstance(metric_type, MetricType) else str(metric_type)

        # Fast idempotency check
        stmt = select(UsageRecord).where(UsageRecord.idempotency_key == idempotency_key)
        existing = session.execute(stmt).scalars().first()
        if existing:
            return existing

        # Ensure organization exists
        org = session.get(Organization, organization_id)
        if not org:
            raise ValidationError(f"Organization ID {organization_id} not found")

        record = UsageRecord(
            organization_id=organization_id,
            metric_type=m_type,
            quantity=float(quantity),
            idempotency_key=idempotency_key.strip(),
            resource_id=resource_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @staticmethod
    def aggregate_usage(
        session: Session,
        organization_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Aggregates metered quantities grouped by metric_type within an optional timeframe."""
        stmt = select(UsageRecord.metric_type, func.sum(UsageRecord.quantity)).where(
            UsageRecord.organization_id == organization_id
        )
        if start_time:
            stmt = stmt.where(UsageRecord.recorded_at >= start_time)
        if end_time:
            stmt = stmt.where(UsageRecord.recorded_at <= end_time)

        stmt = stmt.group_by(UsageRecord.metric_type)
        rows = session.execute(stmt).all()
        return {row[0]: float(row[1]) for row in rows}

    @staticmethod
    def get_metered_summary(
        session: Session,
        organization_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Provides a comprehensive summary across all 8 metered resource dimensions."""
        totals = UsageMeteringService.aggregate_usage(
            session=session,
            organization_id=organization_id,
            start_time=start_time,
            end_time=end_time,
        )
        return {
            "organization_id": organization_id,
            "period_start": start_time.isoformat() if start_time else None,
            "period_end": end_time.isoformat() if end_time else None,
            "metrics": {m.value: totals.get(m.value, 0.0) for m in MetricType},
        }
