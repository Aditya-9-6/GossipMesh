import pytest
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.auth.mfa import (
    generate_totp_secret,
    get_totp_token,
    verify_totp_code,
    generate_recovery_codes,
    MFAService,
    MFAAuthenticationError,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_totp_generation_and_verification():
    secret = generate_totp_secret()
    assert len(secret) >= 16

    # Generate current token
    code = get_totp_token(secret)
    assert len(code) == 6
    assert code.isdigit()

    # Verification should succeed
    assert verify_totp_code(secret, code) is True

    # Bad codes should fail
    assert verify_totp_code(secret, "000000" if code != "000000" else "111111") is False
    assert verify_totp_code(secret, "abc123") is False


def test_totp_time_drift_window():
    secret = generate_totp_secret()
    # Code generated 25 seconds in the past should pass with window=1
    past_code = get_totp_token(secret, t=time.time() - 25)
    assert verify_totp_code(secret, past_code, window=1) is True


def test_recovery_codes():
    codes = generate_recovery_codes(8)
    assert len(codes) == 8
    assert all("-" in c for c in codes)


def test_mfa_service_workflow(db_session):
    user = User(email="mfa_admin@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()

    secret, recovery = MFAService.setup_mfa_for_user(user.id, db_session)
    assert user.mfa_enabled is False
    assert user.mfa_secret == secret

    # Invalid activation fails
    with pytest.raises(MFAAuthenticationError, match="Invalid MFA TOTP"):
        MFAService.verify_and_activate(user.id, "999999", db_session)

    # Valid activation succeeds
    valid_code = get_totp_token(secret)
    activated = MFAService.verify_and_activate(user.id, valid_code, db_session)
    assert activated is True
    assert user.mfa_enabled is True

    # Step-up authentication test
    assert MFAService.require_step_up_auth(user, valid_code, "delete_organization") is True

    # Step-up authentication fails on invalid code
    with pytest.raises(MFAAuthenticationError, match="Invalid TOTP step-up"):
        MFAService.require_step_up_auth(user, "000000", "delete_organization")
