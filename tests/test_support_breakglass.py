from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.audit import AuditEvent
from gossipmesh.enterprise.break_glass import BreakGlassControlService
from gossipmesh.core.exceptions import AuthorizationError, ValidationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="CustomerOrg")
    session.add(org)
    session.commit()

    yield session
    session.close()


def test_break_glass_request_validation(db_session):
    service = BreakGlassControlService()

    # Short reason rejected
    with pytest.raises(ValidationError) as exc_info:
        service.request_access(
            session=db_session,
            support_user_id=10,
            organization_id=1,
            reason="debugging",
            ticket_id="SUP-101",
        )
    assert "detailed operational justification" in str(exc_info.value)

    # Empty ticket rejected
    with pytest.raises(ValidationError) as exc_info:
        service.request_access(
            session=db_session,
            support_user_id=10,
            organization_id=1,
            reason="Valid operational debugging request for sandbox issue",
            ticket_id="",
        )
    assert "valid customer support ticket" in str(exc_info.value)

    # Excessive duration rejected (>4 hours)
    with pytest.raises(ValidationError) as exc_info:
        service.request_access(
            session=db_session,
            support_user_id=10,
            organization_id=1,
            reason="Valid operational debugging request for sandbox issue",
            ticket_id="SUP-101",
            duration_hours=5,
        )
    assert "must be between 1 and 4 hours" in str(exc_info.value)


def test_least_privilege_source_code_protection(db_session):
    service = BreakGlassControlService()

    # Grant metadata-only session (default)
    grant = service.request_access(
        session=db_session,
        support_user_id=10,
        organization_id=1,
        reason="Investigating failed indexing queue on worker-3",
        ticket_id="SUP-101",
        duration_hours=2,
        allow_source_code_access=False,
    )
    assert grant.id is not None

    # Normal metadata access passes
    verified = service.verify_access(support_user_id=10, organization_id=1, requesting_source_code=False)
    assert verified.id == grant.id

    # Source code access blocked by least-privilege policy
    with pytest.raises(AuthorizationError) as exc_info:
        service.verify_access(support_user_id=10, organization_id=1, requesting_source_code=True)
    assert "does not permit proprietary source code access" in str(exc_info.value)


def test_session_revocation(db_session):
    service = BreakGlassControlService()

    grant = service.request_access(
        session=db_session,
        support_user_id=10,
        organization_id=1,
        reason="Investigating webhook HMAC delivery failure",
        ticket_id="SUP-102",
    )

    # Revoke session
    service.revoke_access(db_session, grant.id, revoked_by_id=1, reason="Investigation completed")

    # Access is now blocked
    with pytest.raises(AuthorizationError) as exc_info:
        service.verify_access(support_user_id=10, organization_id=1)
    assert "No active or valid break-glass support session found" in str(exc_info.value)

    # Audit events verified
    events = db_session.query(AuditEvent).filter_by(organization_id=1).all()
    actions = {e.action for e in events}
    assert "support.break_glass_granted" in actions
    assert "support.break_glass_revoked" in actions
