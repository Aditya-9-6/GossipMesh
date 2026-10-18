import pytest
from fastapi.testclient import TestClient
from gossipmesh.api import app

client = TestClient(app)

def test_approval_gate_lifecycle():
    # The approval gate endpoint requires authentication credentials.
    # We supply a mock authorization token header or basic auth token as expected by the API auth middleware/dependency.
    headers = {"Authorization": "Bearer test-token"}
    response = client.post(
        "/api/v1/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1
        },
        headers=headers
    );
    # If authentication succeeds or returns 201 as configured in mock environment
    assert response.status_code in (201, 200)
