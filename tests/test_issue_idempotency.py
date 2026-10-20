import pytest
from sqlalchemy.orm import Session
from gossipmesh.workflows.idempotency import IssueIdempotencyManager
from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.webhooks import WebhookEvent


def test_payload_hash_consistency():
    payload1 = {"issue": {"number": 42, "title": "Fix bug"}, "repository": {"full_name": "test/repo"}}
    payload2 = {"repository": {"full_name": "test/repo"}, "issue": {"title": "Fix bug", "number": 42}}

    hash1 = IssueIdempotencyManager.compute_payload_hash(payload1)
    hash2 = IssueIdempotencyManager.compute_payload_hash(payload2)

    assert hash1 == hash2


def test_idempotency_check_no_prior_attempts(mock_db_session: Session):
    result = IssueIdempotencyManager.check_existing_pr_or_branch(mock_db_session, "test/repo", 999)
    assert result["can_proceed"] is True
    assert result["branch_exists"] is False
    assert result["pr_exists"] is False
    assert result["prior_attempts_count"] == 0


def test_idempotency_check_with_prior_attempt(mock_db_session: Session):
    repo_full_name = "test/repo"
    issue_number = 123

    IssueIdempotencyManager.record_attempt(mock_db_session, repo_full_name, issue_number, details={"status": "success"})

    result = IssueIdempotencyManager.check_existing_pr_or_branch(mock_db_session, repo_full_name, issue_number)
    assert result["can_proceed"] is False
    assert result["branch_exists"] is True
    assert result["pr_exists"] is True
    assert result["prior_attempts_count"] == 1
