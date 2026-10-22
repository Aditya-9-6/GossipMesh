from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.billing import UsageRecord
from gossipmesh.billing.usage_metering import MetricType, UsageMeteringService
from gossipmesh.core.exceptions import ValidationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="TestOrg")
    session.add(org)
    session.commit()

    yield session
    session.close()


def test_record_all_eight_metrics(db_session):
    metrics = [
        (MetricType.REVIEWED_PRS, 1.0, "pr_scan_101"),
        (MetricType.CHANGED_LINES, 450.0, "pr_lines_101"),
        (MetricType.AI_TOKENS, 15420.0, "pr_tokens_101"),
        (MetricType.INDEXING_OPERATIONS, 2.0, "repo_idx_99"),
        (MetricType.SANDBOX_MINUTES, 4.5, "job_sbx_303"),
        (MetricType.SEATS, 8.0, "active_seats_nov"),
        (MetricType.STORAGE_BYTES, 1024.0 * 1024.0 * 50.0, "artifact_storage_nov"),
        (MetricType.PREMIUM_SCANNERS, 1.0, "semgrep_pro_run_44"),
    ]

    for m_type, qty, res_id in metrics:
        rec = UsageMeteringService.record_usage(
            session=db_session,
            organization_id=1,
            metric_type=m_type,
            quantity=qty,
            idempotency_key=f"idem_{res_id}",
            resource_id=res_id,
        )
        assert rec.id is not None
        assert rec.quantity == qty
        assert rec.metric_type == m_type.value

    # Check aggregation across all metrics
    summary = UsageMeteringService.get_metered_summary(db_session, organization_id=1)
    assert summary["organization_id"] == 1
    assert summary["metrics"][MetricType.REVIEWED_PRS.value] == 1.0
    assert summary["metrics"][MetricType.CHANGED_LINES.value] == 450.0
    assert summary["metrics"][MetricType.AI_TOKENS.value] == 15420.0
    assert summary["metrics"][MetricType.SANDBOX_MINUTES.value] == 4.5
    assert summary["metrics"][MetricType.SEATS.value] == 8.0
    assert summary["metrics"][MetricType.PREMIUM_SCANNERS.value] == 1.0


def test_usage_idempotency_prevents_double_counting(db_session):
    idem_key = "unique_idem_charge_007"

    # First record
    rec1 = UsageMeteringService.record_usage(
        session=db_session,
        organization_id=1,
        metric_type=MetricType.AI_TOKENS,
        quantity=5000.0,
        idempotency_key=idem_key,
    )

    # Duplicate call with same idempotency key
    rec2 = UsageMeteringService.record_usage(
        session=db_session,
        organization_id=1,
        metric_type=MetricType.AI_TOKENS,
        quantity=5000.0,
        idempotency_key=idem_key,
    )

    assert rec1.id == rec2.id

    # Aggregated total must still be 5000, NOT 10000
    totals = UsageMeteringService.aggregate_usage(db_session, organization_id=1)
    assert totals[MetricType.AI_TOKENS.value] == 5000.0


def test_negative_quantity_and_invalid_org_rejected(db_session):
    with pytest.raises(ValidationError) as exc_info:
        UsageMeteringService.record_usage(
            session=db_session,
            organization_id=1,
            metric_type=MetricType.REVIEWED_PRS,
            quantity=-5.0,
            idempotency_key="neg_idem",
        )
    assert "cannot be negative" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        UsageMeteringService.record_usage(
            session=db_session,
            organization_id=999,  # Nonexistent
            metric_type=MetricType.REVIEWED_PRS,
            quantity=1.0,
            idempotency_key="org_not_found",
        )
    assert "Organization ID 999 not found" in str(exc_info.value)
