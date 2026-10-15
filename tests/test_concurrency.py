import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from gossipmesh.models.base import Base
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.models.repository import Repository
from gossipmesh.models.organization import Organization

class TestConcurrency(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        db = self.SessionLocal()
        org = Organization(name="Test Org")
        db.add(org)
        db.commit()
        self.org_id = org.id
        db.close()

    def tearDown(self):
        Base.metadata.drop_all(self.engine)

    def test_workflow_optimistic_concurrency(self):
        db1 = self.SessionLocal()
        db2 = self.SessionLocal()

        repo = Repository(organization_id=self.org_id, github_id=123, name="test", full_name="test/test")
        db1.add(repo)
        db1.commit()

        workflow = Workflow(organization_id=self.org_id, repository_id=repo.id)
        db1.add(workflow)
        db1.commit()

        w1 = db1.query(Workflow).filter_by(id=workflow.id).first()
        w2 = db2.query(Workflow).filter_by(id=workflow.id).first()

        w1.status = "running"
        db1.commit()

        w2.status = "completed"
        with self.assertRaises(StaleDataError):
            db2.commit()

    def test_job_optimistic_concurrency(self):
        db1 = self.SessionLocal()
        db2 = self.SessionLocal()

        repo = Repository(organization_id=self.org_id, github_id=456, name="test2", full_name="test/test2")
        db1.add(repo)
        db1.commit()

        workflow = Workflow(organization_id=self.org_id, repository_id=repo.id)
        db1.add(workflow)
        db1.commit()

        job = Job(workflow_id=workflow.id, agent_name="test_agent")
        db1.add(job)
        db1.commit()

        j1 = db1.query(Job).filter_by(id=job.id).first()
        j2 = db2.query(Job).filter_by(id=job.id).first()

        j1.status = "running"
        db1.commit()

        j2.status = "completed"
        with self.assertRaises(StaleDataError):
            db2.commit()

    def test_repository_optimistic_concurrency(self):
        db1 = self.SessionLocal()
        db2 = self.SessionLocal()

        repo = Repository(organization_id=self.org_id, github_id=789, name="test3", full_name="test/test3")
        db1.add(repo)
        db1.commit()

        r1 = db1.query(Repository).filter_by(id=repo.id).first()
        r2 = db2.query(Repository).filter_by(id=repo.id).first()

        r1.default_branch = "dev"
        db1.commit()

        r2.default_branch = "master"
        with self.assertRaises(StaleDataError):
            db2.commit()

if __name__ == '__main__':
    unittest.main()
