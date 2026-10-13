import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.exc import StaleDataError
import os

from gossipmesh.models.base import Base
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.models.repository import Repository
from gossipmesh.models.organization import Organization
from gossipmesh.models.user import User

@pytest.fixture
def concurrency_db_session():
    # Use in-memory SQLite for testing concurrency control
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # We need to setup some base data required by foreign keys (organization)
    db = SessionLocal()
    org = Organization(name="Test Org")
    db.add(org)
    db.commit()

    yield engine, org.id
    Base.metadata.drop_all(engine)


def test_workflow_optimistic_concurrency(concurrency_db_session):
    engine, org_id = concurrency_db_session
    SessionLocal = sessionmaker(bind=engine)

    db1 = SessionLocal()
    db2 = SessionLocal()

    # Setup initial repository since it's required for workflow
    repo = Repository(organization_id=org_id, github_id=123, name="test", full_name="test/test")
    db1.add(repo)
    db1.commit()

    workflow = Workflow(organization_id=org_id, repository_id=repo.id)
    db1.add(workflow)
    db1.commit()

    w1 = db1.query(Workflow).filter_by(id=workflow.id).first()
    w2 = db2.query(Workflow).filter_by(id=workflow.id).first()

    w1.status = "running"
    db1.commit()

    w2.status = "completed"
    with pytest.raises(StaleDataError):
        db2.commit()

def test_job_optimistic_concurrency(concurrency_db_session):
    engine, org_id = concurrency_db_session
    SessionLocal = sessionmaker(bind=engine)

    db1 = SessionLocal()
    db2 = SessionLocal()

    # Setup initial repository and workflow
    repo = Repository(organization_id=org_id, github_id=456, name="test2", full_name="test/test2")
    db1.add(repo)
    db1.commit()

    workflow = Workflow(organization_id=org_id, repository_id=repo.id)
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
    with pytest.raises(StaleDataError):
        db2.commit()

def test_repository_optimistic_concurrency(concurrency_db_session):
    engine, org_id = concurrency_db_session
    SessionLocal = sessionmaker(bind=engine)

    db1 = SessionLocal()
    db2 = SessionLocal()

    repo = Repository(organization_id=org_id, github_id=789, name="test3", full_name="test/test3")
    db1.add(repo)
    db1.commit()

    r1 = db1.query(Repository).filter_by(id=repo.id).first()
    r2 = db2.query(Repository).filter_by(id=repo.id).first()

    r1.default_branch = "dev"
    db1.commit()

    r2.default_branch = "master"
    with pytest.raises(StaleDataError):
        db2.commit()
