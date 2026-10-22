import hmac
import hashlib
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.audit import AuditEvent
from gossipmesh.notifications.service import (
    NotificationChannel,
    NotificationDispatcher,
    NotificationEvent,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="NotifyCorp")
    session.add(org)
    session.commit()

    yield session
    session.close()


def test_slack_formatting_and_secret_redaction():
    dispatcher = NotificationDispatcher()

    payload = dispatcher.format_slack_message(
        event=NotificationEvent.CRITICAL_FINDINGS,
        title="Critical Vulnerability Detected",
        message="SQL injection in auth token query with token: sk-live-secretkey123456789012345",
        metadata={"token": "ghp_1234567890abcdef1234567890abcdef1234"},
    )

    attachments = payload["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["color"] == "#e11d48"  # Red for critical

    raw_json = json.dumps(payload)
    # Secrets must be redacted
    assert "sk-live-secretkey" not in raw_json
    assert "ghp_" not in raw_json
    assert "[REDACTED_SECRET]" in raw_json


def test_webhook_payload_signing():
    secret = "whsec_supersecret_notification_key"
    dispatcher = NotificationDispatcher(outbound_webhook_secret=secret)

    payload = dispatcher.format_webhook_payload(
        event=NotificationEvent.REVIEW_COMPLETED,
        organization_id=1,
        title="PR #102 Review Complete",
        message="Autonomous gate passed successfully.",
    )
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = dispatcher.sign_webhook_payload(payload_bytes)

    # Verify signature
    expected_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    assert signature == expected_sig


def test_dispatch_all_notification_events(db_session):
    dispatcher = NotificationDispatcher()

    events = [
        (NotificationEvent.REVIEW_COMPLETED, "PR #50 Reviewed"),
        (NotificationEvent.CRITICAL_FINDINGS, "2 Critical findings detected"),
        (NotificationEvent.JOB_FAILED, "Execution sandbox timed out"),
        (NotificationEvent.APPROVAL_REQUIRED, "Human approval requested for high risk PR"),
        (NotificationEvent.USAGE_LIMIT_WARNING, "80% of monthly PR review quota reached"),
        (NotificationEvent.BILLING_EVENT, "Invoice #109 paid successfully"),
    ]

    for ev, title in events:
        res = dispatcher.dispatch(
            session=db_session,
            event=ev,
            organization_id=1,
            title=title,
            message="Detailed automated message body.",
            channels=[NotificationChannel.SLACK, NotificationChannel.WEBHOOK],
        )
        assert "slack" in res
        assert "webhook" in res

    # Verify audit records for all 6 events
    audits = db_session.query(AuditEvent).filter(AuditEvent.organization_id == 1).all()
    assert len(audits) == 6
    audit_actions = {a.action for a in audits}
    assert "notification.review_completed" in audit_actions
    assert "notification.critical_findings" in audit_actions
    assert "notification.job_failed" in audit_actions
    assert "notification.approval_required" in audit_actions
    assert "notification.usage_limit_warning" in audit_actions
    assert "notification.billing_event" in audit_actions
