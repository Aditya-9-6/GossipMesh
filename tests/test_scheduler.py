"""Comprehensive unit tests for Workflow Scheduler, Priorities, Plan Limits, and Graceful Shutdown (Task 64)."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository, IndexState, RepositoryPolicy
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.core.exceptions import RateLimitError
from gossipmesh.runtime.scheduler import (
    WorkflowScheduler,
    JobPriority,
    shutdown_controller,
)


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
        org = Organization(id=1, name="Sched Org")
        repo = Repository(id=1, organization_id=1, github_id=888, name="sched-repo", full_name="org/sched-repo", default_branch="main")
        session.add_all([org, repo])
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_shutdown():
    shutdown_controller.reset()
    yield
    shutdown_controller.reset()


def test_priority_calculation():
    # Free tier
    assert WorkflowScheduler.calculate_effective_priority(JobPriority.LOW, "free") == 10
    assert WorkflowScheduler.calculate_effective_priority(JobPriority.NORMAL, "free") == 50
    assert WorkflowScheduler.calculate_effective_priority(JobPriority.CRITICAL, "free") == 100

    # Enterprise tier (+30 boost)
    assert WorkflowScheduler.calculate_effective_priority(JobPriority.LOW, "enterprise") == 40
    assert WorkflowScheduler.calculate_effective_priority(JobPriority.NORMAL, "enterprise") == 80
    assert WorkflowScheduler.calculate_effective_priority(JobPriority.CRITICAL, "enterprise") == 130


def test_priority_dispatch_ordering(db_session):
    # 1. Enqueue low-priority background indexing (Effective priority: 10)
    wf_low, job_low = WorkflowScheduler.schedule_indexing(
        db=db_session, repository_id=1, organization_id=1, plan_tier="free", force=True
    )

    # 2. Enqueue normal PR review (Effective priority: 50)
    wf_norm, job_norm = WorkflowScheduler.enqueue_review(
        db=db_session, repository_id=1, organization_id=1, pr_number=101, is_user_triggered=False, plan_tier="free"
    )

    # 3. Enqueue critical enterprise PR review (Effective priority: 100 + 30 = 130)
    wf_crit, job_crit = WorkflowScheduler.enqueue_review(
        db=db_session, repository_id=1, organization_id=1, pr_number=102, is_user_triggered=True, plan_tier="enterprise"
    )

    # Dispatch: Job with highest priority (130) MUST be dispatched first
    worker_id = "worker-sched-1"
    j1, _ = WorkflowScheduler.dispatch_next_job(db=db_session, worker_id=worker_id)
    assert j1 is not None
    assert j1.id == job_crit.id

    # Next: Normal review (50)
    j2, _ = WorkflowScheduler.dispatch_next_job(db=db_session, worker_id=worker_id)
    assert j2 is not None
    assert j2.id == job_norm.id

    # Next: Low priority indexing (10)
    j3, _ = WorkflowScheduler.dispatch_next_job(db=db_session, worker_id=worker_id)
    assert j3 is not None
    assert j3.id == job_low.id

    # Queue empty
    j4, _ = WorkflowScheduler.dispatch_next_job(db=db_session, worker_id=worker_id)
    assert j4 is None


def test_customer_plan_queue_limits(db_session):
    # Free tier has limit of 5 pending jobs
    for i in range(5):
        WorkflowScheduler.enqueue_review(
            db=db_session, repository_id=1, organization_id=1, pr_number=200 + i, plan_tier="free"
        )

    # 6th attempt must raise RateLimitError
    with pytest.raises(RateLimitError) as exc:
        WorkflowScheduler.enqueue_review(
            db=db_session, repository_id=1, organization_id=1, pr_number=206, plan_tier="free"
        )
    assert "Customer plan queue limit reached" in str(exc.value.message)


def test_scheduled_indexing_frequency(db_session):
    # Setup index state with recent indexing
    idx_state = IndexState(
        repository_id=1,
        status="completed",
        last_indexed_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    policy = RepositoryPolicy(repository_id=1, scan_frequency_hours=24)
    db_session.add_all([idx_state, policy])
    db_session.commit()

    # Should not schedule because 2 hours < 24 hours
    res = WorkflowScheduler.schedule_indexing(db=db_session, repository_id=1, organization_id=1, force=False)
    assert res is None

    # Forced indexing should schedule immediately
    res_forced = WorkflowScheduler.schedule_indexing(db=db_session, repository_id=1, organization_id=1, force=True)
    assert res_forced is not None
    wf, job = res_forced
    assert job.agent_name == "repository_indexer"


def test_graceful_shutdown(db_session):
    shutdown_controller.initiate_shutdown()
    assert shutdown_controller.is_shutting_down is True

    # New review enqueue should be rejected
    with pytest.raises(RuntimeError) as exc:
        WorkflowScheduler.enqueue_review(
            db=db_session, repository_id=1, organization_id=1, pr_number=300
        )
    assert "Scheduler is shutting down" in str(exc.value)

    # Dispatch returns None
    j, _ = WorkflowScheduler.dispatch_next_job(db=db_session, worker_id="w-shutdown")
    assert j is None
