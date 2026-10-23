"""Comprehensive unit tests for Worker Ownership, Leases, and Crash Recovery (Task 63)."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.models.base import Base
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository
from gossipmesh.core.exceptions import ConflictError
from gossipmesh.runtime.worker_lease import WorkerLeaseManager


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Seed required foreign keys
        org = Organization(id=1, name="Lease Org")
        repo = Repository(
            id=1, organization_id=1, github_id=555, name="repo", full_name="org/repo", default_branch="main"
        )
        wf = Workflow(id=1, organization_id=1, repository_id=1, status="running")
        session.add_all([org, repo, wf])
        session.commit()
        yield session
    finally:
        session.close()


def test_worker_id_generation():
    wid1 = WorkerLeaseManager.generate_worker_id(prefix="runner")
    wid2 = WorkerLeaseManager.generate_worker_id(prefix="runner")
    assert wid1.startswith("runner-")
    assert wid1 != wid2


def test_job_lease_acquisition_and_completion(db_session):
    job = Job(id=10, workflow_id=1, agent_name="pr_reviewer", status="pending")
    db_session.add(job)
    db_session.commit()

    worker_id = "worker-host-100"
    claimed_job, lease_token = WorkerLeaseManager.acquire_job_lease(
        db=db_session, worker_id=worker_id, lease_duration_seconds=120
    )

    assert claimed_job is not None
    assert claimed_job.id == 10
    assert claimed_job.status == "running"
    assert claimed_job.worker_id == worker_id
    assert claimed_job.attempts == 1
    assert lease_token is not None

    # Complete job successfully
    completed = WorkerLeaseManager.complete_job(
        db=db_session,
        job_id=10,
        worker_id=worker_id,
        lease_token=lease_token,
        result_state={"reviews": "passed"},
    )
    assert completed.status == "completed"
    assert completed.state["reviews"] == "passed"
    assert completed.lease_token is None


def test_heartbeat_and_lease_extension(db_session):
    job = Job(id=20, workflow_id=1, agent_name="code_fixer", status="pending")
    db_session.add(job)
    db_session.commit()

    worker_id = "worker-heartbeat-1"
    _, lease_token = WorkerLeaseManager.acquire_job_lease(db=db_session, worker_id=worker_id, lease_duration_seconds=30)

    # Valid heartbeat extends lease
    success = WorkerLeaseManager.heartbeat(
        db=db_session, job_id=20, worker_id=worker_id, lease_token=lease_token, extend_seconds=120
    )
    assert success is True

    # Heartbeat with invalid token fails with ConflictError (fencing)
    with pytest.raises(ConflictError) as exc:
        WorkerLeaseManager.heartbeat(db=db_session, job_id=20, worker_id=worker_id, lease_token="stolen-wrong-token")
    assert "Fencing violation" in str(exc.value.message)


def test_duplicate_execution_prevention_fencing(db_session):
    # Job acquired by Worker A
    job = Job(id=30, workflow_id=1, agent_name="security_scanner", status="pending")
    db_session.add(job)
    db_session.commit()

    worker_a = "worker-A"
    _, lease_a = WorkerLeaseManager.acquire_job_lease(db=db_session, worker_id=worker_a, lease_duration_seconds=1)

    # Simulate lease expiry for Worker A
    db_session.expire_all()
    j = db_session.query(Job).filter(Job.id == 30).first()
    j.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()

    # Worker B claims the abandoned job
    worker_b = "worker-B"
    _, lease_b = WorkerLeaseManager.acquire_job_lease(db=db_session, worker_id=worker_b, lease_duration_seconds=60)
    assert lease_b != lease_a

    # Worker A now finishes late and attempts to complete the job
    with pytest.raises(ConflictError) as exc:
        WorkerLeaseManager.complete_job(
            db=db_session, job_id=30, worker_id=worker_a, lease_token=lease_a, result_state={"stale": True}
        )
    assert "Duplicate execution prevented" in str(exc.value.message)

    # Worker B finishes and completes legitimately
    done_b = WorkerLeaseManager.complete_job(
        db=db_session, job_id=30, worker_id=worker_b, lease_token=lease_b, result_state={"valid": True}
    )
    assert done_b.status == "completed"
    assert done_b.state["valid"] is True


def test_crash_recovery_sweep(db_session):
    past = datetime.now(timezone.utc) - timedelta(seconds=500)

    # Job 1: 1 attempt (< 3) -> should be recovered to pending
    job1 = Job(
        id=40,
        workflow_id=1,
        agent_name="test_runner",
        status="running",
        attempts=1,
        lease_expires_at=past,
        worker_id="dead-worker-1",
    )
    # Job 2: 3 attempts (>= 3) -> should fail permanently
    job2 = Job(
        id=41,
        workflow_id=1,
        agent_name="test_runner",
        status="running",
        attempts=3,
        lease_expires_at=past,
        worker_id="dead-worker-2",
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    report = WorkerLeaseManager.recover_abandoned_jobs(db_session, max_retries=3)
    assert 40 in report["recovered"]
    assert 41 in report["exhausted"]

    # Verify states in database
    db_session.expire_all()
    j1 = db_session.query(Job).filter(Job.id == 40).first()
    assert j1.status == "pending"
    assert j1.worker_id is None
    assert j1.lease_token is None

    j2 = db_session.query(Job).filter(Job.id == 41).first()
    assert j2.status == "failed"
    assert "Maximum crash recovery retries exceeded" in j2.state["error"]
