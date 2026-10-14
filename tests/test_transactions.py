import unittest
from unittest.mock import patch
from gossipmesh.models.runtime import Workflow, Job, Budget
from gossipmesh.models.audit import AuditEvent
from gossipmesh.runtime.workflow import WorkflowManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.models.base import Base

class TestTransactions(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def tearDown(self):
        self.session.close()

    def test_approve_patch_rollback(self):
        # Setup
        workflow = Workflow(organization_id=1, repository_id=1, status="blocked")
        self.session.add(workflow)

        budget = Budget(organization_id=1, monthly_limit_usd=100.0, current_spend_usd=0.0)
        self.session.add(budget)
        self.session.commit()

        manager = WorkflowManager(self.session)

        # Mock budget record to fail midway
        with patch("gossipmesh.runtime.budget.BudgetManager.record_spend") as mock_rs:
            mock_rs.side_effect = Exception("DB Error")
            with self.assertRaises(Exception):
                manager.approve_patch(workflow.id, actor_id=99)

        # Verify rollback
        self.session.expire_all()
        wf = self.session.query(Workflow).filter(Workflow.id == workflow.id).first()
        self.assertEqual(wf.status, "blocked") # Not changed to running

        # Verify no audit event is saved
        audit = self.session.query(AuditEvent).filter(AuditEvent.action == "workflow_approved").first()
        self.assertIsNone(audit)

        # Verify budget didn't update
        bg = self.session.query(Budget).filter(Budget.organization_id == 1).first()
        self.assertEqual(bg.current_spend_usd, 0.0)

    def test_create_workflow_with_job_rollback(self):
        manager = WorkflowManager(self.session)

        # We can just patch db.add or flush
        with patch.object(self.session, 'flush', side_effect=Exception("DB flush failed")):
            with self.assertRaises(Exception):
                manager.create_workflow_with_job(organization_id=1, repository_id=1, agent_name="agent-1", actor_id=99)

        # Verify rollback
        self.session.expire_all()
        wfs = self.session.query(Workflow).all()
        self.assertEqual(len(wfs), 0)

        jobs = self.session.query(Job).all()
        self.assertEqual(len(jobs), 0)

        audits = self.session.query(AuditEvent).all()
        self.assertEqual(len(audits), 0)

if __name__ == "__main__":
    unittest.main()
