import unittest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository
from gossipmesh.runtime.workflow import WorkflowManager


class TestCancellationAndDeadlines(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        db = self.SessionLocal()
        org = Organization(name="Test Org")
        db.add(org)
        db.flush()
        self.org_id = org.id

        repo = Repository(organization_id=self.org_id, github_id=123, name="test", full_name="test/test")
        db.add(repo)
        db.flush()
        self.repo_id = repo.id

        db.commit()
        db.close()

    def tearDown(self):
        Base.metadata.drop_all(self.engine)

    def test_workflow_cancelled_returns_true(self):
        db = self.SessionLocal()
        manager = WorkflowManager(db)

        workflow = Workflow(organization_id=self.org_id, repository_id=self.repo_id, status="cancelled")
        db.add(workflow)
        db.commit()

        self.assertTrue(manager.check_cancellation(workflow.id))
        db.close()

    def test_workflow_deadline_exceeded_returns_true_and_fails(self):
        db = self.SessionLocal()
        manager = WorkflowManager(db)

        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        workflow = Workflow(
            organization_id=self.org_id, repository_id=self.repo_id, status="running", deadline=past_deadline
        )
        db.add(workflow)
        db.flush()

        job = Job(workflow_id=workflow.id, agent_name="test_agent", status="running")
        db.add(job)
        db.commit()

        self.assertTrue(manager.check_cancellation(workflow.id))

        db.refresh(workflow)
        db.refresh(job)

        self.assertEqual(workflow.status, "failed")
        self.assertEqual(job.status, "cancelled")
        self.assertEqual(job.state.get("error"), "deadline_exceeded")

        db.close()

    def test_workflow_not_cancelled_and_within_deadline_returns_false(self):
        db = self.SessionLocal()
        manager = WorkflowManager(db)

        future_deadline = datetime.now(timezone.utc) + timedelta(hours=1)
        workflow = Workflow(
            organization_id=self.org_id, repository_id=self.repo_id, status="running", deadline=future_deadline
        )
        db.add(workflow)
        db.commit()

        self.assertFalse(manager.check_cancellation(workflow.id))

        db.refresh(workflow)
        self.assertEqual(workflow.status, "running")
        db.close()


if __name__ == "__main__":
    unittest.main()
