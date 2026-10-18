import pytest
from fastapi.testclient import TestClient
from gossipmesh.api import app
from gossipmesh.models.user import User
from gossipmesh.api.deps import get_current_user

client = TestClient(app)

async def override_get_current_user():
    return User(id="test-user-id", email="test@example.com")

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
    data = response.json()
    approval_id = data["id"]
    assert data["status"] == "pending"
    assert data["commit_sha"] == "abc1234"

    res_get = client.get(f"/api/v1/approvals/{approval_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    res_decide = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"}
    )
    assert res_decide.status_code == 200
    decide_data = res_decide.json()
    assert decide_data["status"] == "approved"
    assert decide_data["approver_id"] is not None
    assert decide_data["approved_at"] is not None
