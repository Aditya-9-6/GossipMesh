import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.approval import ApprovalGate

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "approver@gossipmesh.test").first()
        if not user:
            user = User(email="approver@gossipmesh.test", hashed_password="dummy", is_active=True, is_superuser=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()

app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_user] = override_get_current_user

client = TestClient(app)

def test_approval_gate_lifecycle():
    # Create approval request
    response = client.post(
        "/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1
        }
    )
    assert response.status_code == 201
    data = response.json()
    approval_id = data["id"]
    assert data["status"] == "pending"
    assert data["commit_sha"] == "abc1234"

    # Get approval status
    res_get = client.get(f"/approvals/{approval_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    # Approve
    res_decide = client.post(
        f"/approvals/{approval_id}/decision",
        json={"decision": "approved"}
    )
    assert res_decide.status_code == 200
    decide_data = res_decide.json()
    assert decide_data["status"] == "approved"
    assert decide_data["approver_id"] is not None
    assert decide_data["approved_at"] is not None

def test_approval_gate_not_found():
    res = client.get("/approvals/999999")
    assert res.status_code == 404

    res_decide = client.post(
        "/approvals/999999/decision",
        json={"decision": "approved"}
    )
    assert res_decide.status_code == 404

def test_approval_gate_invalid_decision():
    response = client.post(
        "/approvals/",
        json={
            "action_type": "push_commit",
            "expires_in_hours": 1
        }
    )
    assert response.status_code == 201
    approval_id = response.json()["id"]

    res_decide = client.post(
        f"/approvals/{approval_id}/decision",
        json={"decision": "invalid_choice"}
    )
    assert res_decide.status_code == 400

def test_approval_gate_expired():
    db = TestingSessionLocal()
    try:
        expired_gate = ApprovalGate(
            action_type="push_commit",
            status="pending",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db.add(expired_gate)
        db.commit()
        db.refresh(expired_gate)
        expired_id = expired_gate.id
    finally:
        db.close()

    # Attempt to decide on expired gate
    res_decide = client.post(
        f"/approvals/{expired_id}/decision",
        json={"decision": "approved"}
    )
    assert res_decide.status_code == 400
