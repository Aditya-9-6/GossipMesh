import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository
from gossipmesh.models.runtime import Budget, Job, Workflow
from gossipmesh.models.audit import AuditEvent
from gossipmesh.billing.cost_controls import (
    BudgetAlertLevel,
    CostControlConfig,
    CostControlsEngine,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="FinTechOrg")
    repo = Repository(id=1, name="core-service", full_name="FinTechOrg/core-service", github_id=12345, organization_id=1)
    budget = Budget(organization_id=1, monthly_limit_usd=100.0, current_spend_usd=20.0)

    session.add(org)
    session.add(repo)
    session.add(budget)
    session.commit()

    yield session
    session.close()


def test_organization_budget_alert_thresholds(db_session):
    engine = CostControlsEngine()

    # Case 1: Normal spend ($20 / $100 = 20%)
    level, details = engine.check_organization_budget(db_session, 1)
    assert level == BudgetAlertLevel.NORMAL
    assert details["ratio"] == 0.2

    # Case 2: Warning spend ($85 / $100 = 85%)
    budget = db_session.query(Budget).filter_by(organization_id=1).first()
    budget.current_spend_usd = 85.0
    db_session.commit()

    level, details = engine.check_organization_budget(db_session, 1)
    assert level == BudgetAlertLevel.WARNING
    assert details["ratio"] == 0.85

    # Check audit event emitted for warning
    events = db_session.query(AuditEvent).filter_by(action="billing.budget_warning").all()
    assert len(events) == 1

    # Case 3: Exceeded spend ($105 / $100 = 105%)
    budget.current_spend_usd = 105.0
    db_session.commit()

    level, details = engine.check_organization_budget(db_session, 1)
    assert level == BudgetAlertLevel.EXCEEDED

    exceeded_events = db_session.query(AuditEvent).filter_by(action="billing.budget_exceeded").all()
    assert len(exceeded_events) == 1


def test_cost_anomaly_detection():
    engine = CostControlsEngine()

    # Normal hourly spend around $5 - $7
    history = [5.10, 6.20, 5.50, 6.80, 5.90, 6.00, 5.40]

    # Spend within normal range
    is_anomaly, msg = engine.detect_cost_anomaly(history, 6.50)
    assert is_anomaly is False
    assert "within normal" in msg

    # Sudden runaway spike to $65.00
    is_anomaly, msg = engine.detect_cost_anomaly(history, 65.00)
    assert is_anomaly is True
    assert "Cost anomaly detected" in msg
    assert "$65.00" in msg

    # Insufficient data
    is_anomaly, msg = engine.detect_cost_anomaly([5.0], 50.0)
    assert is_anomaly is False
    assert "Insufficient historical data" in msg


def test_emergency_shutdown_terminates_active_workflows(db_session):
    engine = CostControlsEngine()

    # Create active workflows & jobs
    wf1 = Workflow(id=1, organization_id=1, repository_id=1, status="running")
    wf2 = Workflow(id=2, organization_id=1, repository_id=1, status="pending")
    wf3 = Workflow(id=3, organization_id=1, repository_id=1, status="completed")  # should remain completed

    job1 = Job(id=1, workflow_id=1, agent_name="reviewer", status="running")
    job2 = Job(id=2, workflow_id=2, agent_name="fixer", status="pending")

    db_session.add_all([wf1, wf2, wf3, job1, job2])
    db_session.commit()

    # Trigger emergency shutdown
    stopped = engine.trigger_emergency_shutdown(
        session=db_session,
        organization_id=1,
        reason="Runaway token consumption anomaly detected",
        actor="automated_cost_watchdog",
    )
    assert stopped == 2

    # Verify statuses
    db_session.refresh(wf1)
    db_session.refresh(wf2)
    db_session.refresh(wf3)
    db_session.refresh(job1)
    db_session.refresh(job2)

    assert wf1.status == "cancelled"
    assert wf2.status == "cancelled"
    assert wf3.status == "completed"
    assert job1.status == "cancelled"
    assert job2.status == "cancelled"

    # Verify audit event
    audit = db_session.query(AuditEvent).filter_by(action="billing.emergency_shutdown_triggered").first()
    assert audit is not None
    assert audit.organization_id == 1
    assert audit.details["workflows_stopped"] == 2
    assert audit.details["actor"] == "automated_cost_watchdog"


def test_provider_cost_alerts():
    engine = CostControlsEngine()

    # Normal spend ($50 / $100) -> None
    assert engine.check_provider_cost_alert("openai", 50.0, 100.0) is None

    # Warning spend ($82 / $100) -> WARNING
    alert_warn = engine.check_provider_cost_alert("gemini", 82.0, 100.0)
    assert alert_warn is not None
    assert alert_warn["severity"] == "WARNING"
    assert "82.0%" in alert_warn["message"]

    # Critical spend ($110 / $100) -> CRITICAL
    alert_crit = engine.check_provider_cost_alert("anthropic", 110.0, 100.0)
    assert alert_crit is not None
    assert alert_crit["severity"] == "CRITICAL"
    assert "exceeded" in alert_crit["message"]
