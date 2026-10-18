import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.api import app
from gossipmesh.api.deps import get_db
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
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Mock current user dependency if needed
from gossipmesh.api.deps import get_current_user
def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "testuser").first()
    if not user:
        user = User(username="testuser", email="test@example.com", hashed_password="fakepass")
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_approval_gate_lifecycle():
    response = client.post(
        "/api/v1/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1
        },
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["action_type"] == "push_commit"
    assert data["status"] == "pending"
    approval_id = data["id"]

    # Get approval gate
    res_get = client.get(f"/api/v1/approvals/{approval_id}", headers={"Authorization": "Bearer test-token"})
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    # Decide approval
    res_decide = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"},
        headers={"Authorization": "Bearer test-token"}
    )
    assert res_decide.status_code == 200
    assert res_decide.json()["status"] == "approved"
