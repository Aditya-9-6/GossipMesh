"""Comprehensive unit tests for Enterprise Idempotency Keys (Task 59)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.models.base import Base
from gossipmesh.core.exceptions import ConflictError
from gossipmesh.core.idempotency import (
    IdempotencyEngine,
    IdempotencyScope,
    IdempotencyStatus,
    IdempotencyContext,
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
        yield session
    finally:
        session.close()


def test_first_time_acquisition_and_cached_replay(db_session):
    key = "idem-workflow-001"
    scope = IdempotencyScope.WORKFLOW_CREATION
    payload = {"repo_id": 12, "commit_sha": "abc1234"}

    # 1. First execution acquires lock
    status, cached_body, cached_code = IdempotencyEngine.acquire(
        db=db_session, key=key, scope=scope, payload=payload, organization_id=1
    )
    assert status == IdempotencyStatus.ACQUIRED
    assert cached_body is None

    # 2. Complete operation
    response_data = {"workflow_id": 999, "status": "queued"}
    IdempotencyEngine.complete(db_session, key=key, response_body=response_data, response_code=201)

    # 3. Re-execution with exact same key & payload returns cached result immediately
    status, cached_body, cached_code = IdempotencyEngine.acquire(
        db=db_session, key=key, scope=scope, payload=payload, organization_id=1
    )
    assert status == IdempotencyStatus.COMPLETED
    assert cached_code == 201
    assert cached_body["workflow_id"] == 999


def test_payload_mismatch_raises_conflict(db_session):
    key = "idem-pr-002"
    scope = IdempotencyScope.PR_CREATION
    original_payload = {"title": "Fix bug in auth", "base": "main"}
    tampered_payload = {"title": "Malicious PR rewrite", "base": "main"}

    # 1. Acquire with original payload and complete
    IdempotencyEngine.acquire(db=db_session, key=key, scope=scope, payload=original_payload)
    IdempotencyEngine.complete(db_session, key=key, response_body={"pr_number": 42})

    # 2. Reusing same key with altered payload must raise ConflictError
    with pytest.raises(ConflictError) as exc:
        IdempotencyEngine.acquire(db=db_session, key=key, scope=scope, payload=tampered_payload)
    assert "different request payload" in str(exc.value.message)


def test_scope_mismatch_raises_conflict(db_session):
    key = "idem-shared-key-003"
    payload = {"data": "test"}

    # Acquire under comments scope
    IdempotencyEngine.acquire(
        db=db_session, key=key, scope=IdempotencyScope.COMMENTS, payload=payload
    )
    IdempotencyEngine.complete(db_session, key=key, response_body={"comment_id": 7})

    # Try to reuse under billing scope
    with pytest.raises(ConflictError) as exc:
        IdempotencyEngine.acquire(
            db=db_session, key=key, scope=IdempotencyScope.BILLING_USAGE, payload=payload
        )
    assert "different scope" in str(exc.value.message)


def test_concurrent_in_progress_lock(db_session):
    key = "idem-webhook-004"
    scope = IdempotencyScope.WEBHOOK_JOB
    payload = {"delivery_id": "wh-9988"}

    # 1. First process acquires in_progress lock
    status, _, _ = IdempotencyEngine.acquire(db=db_session, key=key, scope=scope, payload=payload)
    assert status == IdempotencyStatus.ACQUIRED

    # 2. Concurrent second process attempts to acquire while first is in progress
    with pytest.raises(ConflictError) as exc:
        IdempotencyEngine.acquire(db=db_session, key=key, scope=scope, payload=payload)
    assert "Concurrent operation in progress" in str(exc.value.message)


def test_failure_and_retry_release(db_session):
    key = "idem-artifact-005"
    scope = IdempotencyScope.ARTIFACT_OPERATION
    payload = {"artifact_name": "build.tar.gz"}

    # 1. Acquire
    status, _, _ = IdempotencyEngine.acquire(db=db_session, key=key, scope=scope, payload=payload)
    assert status == IdempotencyStatus.ACQUIRED

    # 2. Simulate failure with retry allowed
    IdempotencyEngine.fail(db_session, key=key, allow_retry=True)

    # 3. Subsequent retry should successfully re-acquire
    status_retry, _, _ = IdempotencyEngine.acquire(db=db_session, key=key, scope=scope, payload=payload)
    assert status_retry == IdempotencyStatus.ACQUIRED


def test_all_operational_scopes_supported(db_session):
    test_cases = [
        (IdempotencyScope.WORKFLOW_CREATION, {"repo": "gossipmesh"}),
        (IdempotencyScope.WEBHOOK_JOB, {"event": "pull_request"}),
        (IdempotencyScope.COMMENTS, {"line": 42, "text": "LGTM"}),
        (IdempotencyScope.PR_CREATION, {"head": "fix/123", "base": "main"}),
        (IdempotencyScope.BILLING_USAGE, {"tokens": 500, "cents": 25}),
        (IdempotencyScope.ARTIFACT_OPERATION, {"path": "patch.diff"}),
    ]

    for scope, payload in test_cases:
        key = f"key-{scope.value}"
        status, _, _ = IdempotencyEngine.acquire(db_session, key=key, scope=scope.value, payload=payload)
        assert status == IdempotencyStatus.ACQUIRED
        IdempotencyEngine.complete(db_session, key=key, response_body={"scope": scope.value})

        # Re-check replay
        status_replay, body, _ = IdempotencyEngine.acquire(db_session, key=key, scope=scope.value, payload=payload)
        assert status_replay == IdempotencyStatus.COMPLETED
        assert body["scope"] == scope.value


def test_idempotency_context_manager(db_session):
    key = "ctx-key-006"
    scope = IdempotencyScope.WORKFLOW_CREATION
    payload = {"run_id": "r100"}

    # 1. First run executes block
    executed = False
    with IdempotencyContext(db_session, key=key, scope=scope, payload=payload) as ctx:
        if not ctx.is_cached:
            executed = True
            ctx.complete({"result": "created"}, code=201)

    assert executed is True

    # 2. Second run skips execution block and reads cached response
    executed_second = False
    with IdempotencyContext(db_session, key=key, scope=scope, payload=payload) as ctx:
        if not ctx.is_cached:
            executed_second = True
        else:
            cached = ctx.cached_response

    assert executed_second is False
    assert cached["result"] == "created"
