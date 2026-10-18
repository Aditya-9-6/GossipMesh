import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from gossipmesh.api import app
from gossipmesh.api.deps import get_current_active_user, get_db
from gossipmesh.models.user import User

app.dependency_overrides[get_current_active_user] = lambda: User(
    id="test-user-id",
    email="test@gossipmesh.internal",
    hashed_password="",
    is_active=True,
    is_superuser=False
)
app.dependency_overrides[get_db] = lambda: MagicMock()

client = TestClient(app)

def test_approval_gate_lifecycle():
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
