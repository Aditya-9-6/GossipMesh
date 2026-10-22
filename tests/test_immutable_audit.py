import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.audit import AuditEvent
from gossipmesh.audit.immutable_audit import AuditAction, ImmutableAuditService
from gossipmesh.core.exceptions import ValidationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_record_all_thirteen_audit_events(db_session):
    actions = [
        (AuditAction.AUTH_LOGIN, {"ip": "1.2.3.4"}),
        (AuditAction.AUTH_FAILURE, {"reason": "invalid_credentials"}),
        (AuditAction.ROLE_CHANGED, {"target_user": 4, "new_role": "billing_admin"}),
        (AuditAction.REPO_CONNECTED, {"repo": "org/repo"}),
        (AuditAction.PROVIDER_CREDENTIAL_UPDATED, {"provider": "gemini"}),
        (AuditAction.REVIEW_DISPATCHED, {"pr_number": 42}),
        (AuditAction.FINDING_MODIFIED, {"finding_id": 99, "status": "accepted"}),
        (AuditAction.APPROVAL_GRANTED, {"gate_id": 12}),
        (AuditAction.SANDBOX_EXECUTED, {"command": "pytest -q"}),
        (AuditAction.DATA_EXPORTED, {"format": "json"}),
        (AuditAction.DATA_DELETED, {"retention_days": 30}),
        (AuditAction.BILLING_MUTATED, {"plan": "business"}),
        (AuditAction.SUPPORT_ACCESS_GRANTED, {"ticket": "SUP-101"}),
    ]

    for act, details in actions:
        ev = ImmutableAuditService.record_event(
            session=db_session,
            action=act,
            organization_id=1,
            actor_id=10,
            details=details,
        )
        assert ev.id is not None
        assert ev.action == act.value

    # Verify query
    trail = ImmutableAuditService.query_audit_trail(db_session, organization_id=1, limit=50)
    assert len(trail) == 13


def test_audit_event_immutability(db_session):
    ev = ImmutableAuditService.record_event(
        session=db_session,
        action=AuditAction.AUTH_LOGIN,
        organization_id=1,
        actor_id=5,
    )

    # Attempt to modify audit event -> must be rejected
    ev.action = "tampered.action"
    with pytest.raises(ValidationError) as exc_info:
        db_session.commit()
    assert "strictly immutable" in str(exc_info.value)

    db_session.rollback()

    # Attempt to delete audit event -> must be rejected
    with pytest.raises(ValidationError) as exc_info:
        db_session.delete(ev)
        db_session.commit()
    assert "strictly immutable" in str(exc_info.value)


def test_audit_secret_redaction(db_session):
    details_with_secret = {
        "user_email": "admin@test.com",
        "api_key": "sk-proj-supersecretkey12345678901234567890",
        "token": "ghp_1234567890abcdef1234567890abcdef1234",
    }

    ev = ImmutableAuditService.record_event(
        session=db_session,
        action=AuditAction.PROVIDER_CREDENTIAL_UPDATED,
        organization_id=1,
        actor_id=5,
        details=details_with_secret,
    )

    assert "[REDACTED_SECRET]" in ev.details["api_key"]
    assert "[REDACTED_SECRET]" in ev.details["token"]
    assert "supersecretkey" not in ev.details["api_key"]
