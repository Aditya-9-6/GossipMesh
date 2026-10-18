import pytest
from fastapi.testclient import TestClient
from gossipmesh.api import app
from gossipmesh.api.deps import get_current_user
from gossipmesh.models.user import User

client = TestClient(app)

def mock_get_current_user():
    return User(id="test-user-id", email="test@example.com", is_active=True)

app.dependency_overrides[get_current_user] = mock_get_current_user

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
    assert "approval_id" in data or "id" in data
