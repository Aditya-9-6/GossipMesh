import pytest
from fastapi.testclient import TestClient
from gossipmesh.api import app
from gossipmesh.models.user import User
from gossipmesh.api.deps import get_current_user

client = TestClient(app)

async def override_get_current_user():
    return User(id="test-user-id", email="test@example.com", username="testuser")

app.dependency_overrides[get_current_user] = override_get_current_user

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
