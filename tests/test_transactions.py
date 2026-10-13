import pytest
from unittest.mock import patch
from gossipmesh.models.runtime import Workflow, Job, Budget
from gossipmesh.models.audit import AuditEvent
from gossipmesh.runtime.workflow import WorkflowManager
from gossipmesh.runtime.budget import BudgetManager

def test_approve_patch_rollback(mock_db_session):
    # Setup
    workflow = Workflow(organization_id=1, repository_id=1, status="blocked")
    mock_db_session.add(workflow)

    budget = Budget(organization_id=1, monthly_limit_usd=100.0, current_spend_usd=0.0)
    mock_db_session.add(budget)
    mock_db_session.commit()

    manager = WorkflowManager(mock_db_session)

    # Mock budget record to fail midway
    with patch("gossipmesh.runtime.budget.BudgetManager.record_spend") as mock_rs:
        mock_rs.side_effect = Exception("DB Error")
        with pytest.raises(Exception):
            manager.approve_patch(workflow.id, actor_id=99)

    # Verify rollback
    mock_db_session.expire_all()
    wf = mock_db_session.query(Workflow).filter(Workflow.id == workflow.id).first()
    assert wf.status == "blocked" # Not changed to running

    # Verify no audit event is saved
    audit = mock_db_session.query(AuditEvent).filter(AuditEvent.action == "workflow_approved").first()
    assert audit is None

    # Verify budget didn't update
    bg = mock_db_session.query(Budget).filter(Budget.organization_id == 1).first()
    assert bg.current_spend_usd == 0.0

def test_create_workflow_with_job_rollback(mock_db_session):
    manager = WorkflowManager(mock_db_session)

    with patch("gossipmesh.runtime.workflow.WorkflowManager._evaluate_workflow_state", side_effect=Exception("DB Error")):
        # Let's mock flush to throw an exception to simulate DB failure halfway
        pass

    # We can just patch db.add or flush
    with patch.object(mock_db_session, 'flush', side_effect=Exception("DB flush failed")):
        with pytest.raises(Exception):
            manager.create_workflow_with_job(organization_id=1, repository_id=1, agent_name="agent-1", actor_id=99)

    # Verify rollback
    mock_db_session.expire_all()
    wfs = mock_db_session.query(Workflow).all()
    assert len(wfs) == 0

    jobs = mock_db_session.query(Job).all()
    assert len(jobs) == 0

    audits = mock_db_session.query(AuditEvent).all()
    assert len(audits) == 0
