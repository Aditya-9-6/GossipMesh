"""Comprehensive unit and integration tests for Password Security (Task 41).

Tests:
- Password complexity validation
- Login throttling, progressive delays, and account lockout (brute-force defense)
- Inactive user handling
- Secure password reset tokens and replay prevention
- Password-change session invalidation
"""

import os

os.environ["TESTING"] = "true"

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.session import UserSession, RefreshToken, PasswordResetToken
from gossipmesh.core.security import get_password_hash, verify_password
from gossipmesh.auth.password import validate_password_strength, invalidate_user_sessions
from gossipmesh.auth.throttle import login_throttler


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def test_db(engine):
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine):
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    test_client = TestClient(app, raise_server_exceptions=True)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_throttler():
    login_throttler.reset()
    yield
    login_throttler.reset()


def test_password_strength_validation():
    # Too short (<12 chars)
    valid, err = validate_password_strength("Short1!")
    assert not valid
    assert "at least 12 characters" in err

    # Missing uppercase
    valid, err = validate_password_strength("lowercase1234!")
    assert not valid
    assert "uppercase letter" in err

    # Missing lowercase
    valid, err = validate_password_strength("UPPERCASE1234!")
    assert not valid
    assert "lowercase letter" in err

    # Missing digit
    valid, err = validate_password_strength("NoDigitsHere!!")
    assert not valid
    assert "numeric digit" in err

    # Missing special char
    valid, err = validate_password_strength("NoSpecialChar123")
    assert not valid
    assert "special symbol" in err

    # Common password
    valid, err = validate_password_strength("Password123!")
    assert not valid
    assert "too common" in err

    # Email username in password
    valid, err = validate_password_strength("AliceSecret99#", user_email="alice@company.com")
    assert not valid
    assert "cannot contain parts of your email" in err

    # Valid strong password
    valid, err = validate_password_strength("SuperS3cure#Enterprise99!", user_email="alice@company.com")
    assert valid
    assert err is None


def test_login_throttling_progressive_delay_and_lockout(client, test_db):
    user = User(
        id=101,
        email="target@example.com",
        hashed_password=get_password_hash("CorrectHorseBattery99!"),
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()

    # Attempts 1 & 2: Failures without delay
    for _ in range(2):
        res = client.post(
            "/api/v1/auth/login/access-token",
            data={"username": "target@example.com", "password": "WrongPassword1!"},
        )
        assert res.status_code == 401

    is_locked, _ = login_throttler.check_lockout("target@example.com")
    assert not is_locked

    # Attempts 3 & 4: Record progressive delay
    res = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "target@example.com", "password": "WrongPassword3!"},
    )
    assert res.status_code == 401

    res = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "target@example.com", "password": "WrongPassword4!"},
    )
    assert res.status_code == 401

    # Attempt 5: Account triggers lockout (429)
    res = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "target@example.com", "password": "WrongPassword5!"},
    )
    assert res.status_code == 429
    assert "Account temporarily locked" in res.json()["detail"]

    # Subsequent attempt (even with correct password) rejected while locked
    res = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "target@example.com", "password": "CorrectHorseBattery99!"},
    )
    assert res.status_code == 429

    # Reset throttler to simulate lockout expiration and verify successful login
    login_throttler.reset()
    res = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "target@example.com", "password": "CorrectHorseBattery99!"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_inactive_user_handling(client, test_db):
    user = User(
        id=102,
        email="inactive@example.com",
        hashed_password=get_password_hash("CorrectHorseBattery99!"),
        is_active=False,
    )
    test_db.add(user)
    test_db.commit()

    # Login attempt for deactivated account
    res = client.post(
        "/api/v1/auth/login/access-token",
        data={"username": "inactive@example.com", "password": "CorrectHorseBattery99!"},
    )
    assert res.status_code == 403


def test_secure_password_reset_flow(client, test_db):
    user = User(
        id=103,
        email="resetme@example.com",
        hashed_password=get_password_hash("OldPassword123#"),
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()

    # 1. Request password reset
    res = client.post("/api/v1/auth/password/reset-request", json={"email": "resetme@example.com"})
    assert res.status_code == 200
    token = res.json()["reset_token"]
    assert token is not None

    # 2. Reset with weak password fails
    res = client.post(
        "/api/v1/auth/password/reset-confirm",
        json={"token": token, "new_password": "short"},
    )
    assert res.status_code == 400

    # 3. Reset with valid strong password succeeds
    res = client.post(
        "/api/v1/auth/password/reset-confirm",
        json={"token": token, "new_password": "BrandNewSecurePassword99!"},
    )
    assert res.status_code == 200

    # 4. Replay attack with same token fails
    res = client.post(
        "/api/v1/auth/password/reset-confirm",
        json={"token": token, "new_password": "BrandNewSecurePassword99!"},
    )
    assert res.status_code == 400

    # 5. Verify user can log in with new password
    test_db.expire_all()
    updated_user = test_db.query(User).filter(User.id == 103).first()
    assert verify_password("BrandNewSecurePassword99!", updated_user.hashed_password)


def test_password_change_session_invalidation(client, test_db):
    user = User(
        id=104,
        email="session_user@example.com",
        hashed_password=get_password_hash("CurrentPassword99!"),
        is_active=True,
    )
    test_db.add(user)
    test_db.flush()

    sess1 = UserSession(id=1001, user_id=104, is_active=True)
    sess2 = UserSession(id=1002, user_id=104, is_active=True)
    test_db.add_all([sess1, sess2])
    test_db.flush()

    rt1 = RefreshToken(session_id=1001, jti="jti-1", expires_at=datetime.now(timezone.utc) + timedelta(days=7))
    rt2 = RefreshToken(session_id=1002, jti="jti-2", expires_at=datetime.now(timezone.utc) + timedelta(days=7))
    test_db.add_all([rt1, rt2])
    test_db.commit()

    app.dependency_overrides[deps.get_current_user] = lambda: user

    # 1. Change password with wrong current password fails
    res = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "WrongPassword!", "new_password": "UpdatedPassword99#"},
    )
    assert res.status_code == 400

    # 2. Change password with correct current password and strong new password
    res = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "CurrentPassword99!", "new_password": "UpdatedPassword99#"},
    )
    assert res.status_code == 200

    # 3. Verify ALL previous sessions are invalidated and refresh tokens revoked
    test_db.expire_all()
    sessions = test_db.query(UserSession).filter(UserSession.user_id == 104).all()
    for s in sessions:
        assert s.is_active is False

    tokens = test_db.query(RefreshToken).filter(RefreshToken.session_id.in_([1001, 1002])).all()
    for t in tokens:
        assert t.is_revoked is True
