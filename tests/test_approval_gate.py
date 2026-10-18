import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.api import app
from gossipmesh.api import deps
from gossipmesh.models.base import Base
from gossipmesh.models.user import User

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
    user = db.query(User).filter(User.email == "approver@gossipmesh.test").first()
    if not user:
        user = User(email="approver@gossipmesh.test", hashed_password="dummy", is_active=True, is_superuser=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_user] = override_get_current_user

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
    assert data["status"] == "pending"
    assert "id" in data
    approval_id = data["id"]

    # Test get approval gate
    get_response = client.get(f"/api/v1/approvals/{approval_id}", headers={"Authorization": "Bearer test-token"})
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "pending"

    # Test decide approval gate
    decision_response = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"},
        headers={"Authorization": "Bearer test-token"}
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"
