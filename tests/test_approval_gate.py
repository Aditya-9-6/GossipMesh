import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.api import app
from gossipmesh.models.base import Base
from gossipmesh.api.deps import get_current_user
from gossipmesh.models.user import User

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_current_user():
    return User(id=1, email="test@gossipmesh.com", is_active=True)


app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)


def test_approval_gate_lifecycle():
    Base.metadata.create_all(bind=engine)
    response = client.post(
        "/api/v1/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["action_type"] == "push_commit"
    assert data["status"] == "pending"

    approval_id = data["id"]
    response_decide = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "approved", "reason": "Looks good"}
    )
    assert response_decide.status_code == 200
    assert response_decide.json()["status"] == "approved"
