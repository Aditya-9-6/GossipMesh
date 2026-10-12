import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from gossipmesh.api import app
import os
import hashlib
import hmac
import json

client = TestClient(app)


class TestWebhooks(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.get("ENVIRONMENT")
        os.environ["ENVIRONMENT"] = "development"

    def tearDown(self):
        if self.original_env is not None:
            os.environ["ENVIRONMENT"] = self.original_env
        else:
            del os.environ["ENVIRONMENT"]

    def test_missing_event_header(self):
        response = client.post("/webhooks/github", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"detail": "Missing X-GitHub-Event header"}
        )

    @patch("gossipmesh.workflows.pr_review.PRReviewWorkflow.execute")
    def test_pull_request_event(self, mock_execute):
        payload = {"action": "opened", "pull_request": {"number": 123}}
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "pull_request"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "accepted", "event": "pull_request"}
        )

    @patch("gossipmesh.workflows.issue_solver.IssueSolverWorkflow.execute")
    def test_issues_event(self, mock_execute):
        payload = {"action": "opened", "issue": {"number": 456}}
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "issues"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "accepted", "event": "issues"}
        )

    @patch("gossipmesh.workflows.ci_fixer.CIFixerWorkflow.execute")
    def test_workflow_run_event_failure(self, mock_execute):
        payload = {
            "action": "completed",
            "workflow_run": {"id": 789, "conclusion": "failure"},
        }
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "workflow_run"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "accepted", "event": "workflow_run"}
        )

    def test_signature_verification_failure(self):
        os.environ["GITHUB_WEBHOOK_SECRET"] = "mysecret"
        payload = {"action": "opened", "issue": {"number": 456}}
        response = client.post(
            "/webhooks/github",
            headers={
                "X-GitHub-Event": "issues",
                "X-Hub-Signature-256": "sha256=invalidsignature",
            },
            json=payload,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid signature"})
        del os.environ["GITHUB_WEBHOOK_SECRET"]

    @patch("gossipmesh.workflows.issue_solver.IssueSolverWorkflow.execute")
    def test_signature_verification_success(self, mock_execute):
        secret = "mysecret"
        os.environ["GITHUB_WEBHOOK_SECRET"] = secret
        payload = {"action": "opened", "issue": {"number": 456}}
        payload_bytes = json.dumps(payload).encode("utf-8")
        hash_object = hmac.new(
            secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256
        )
        signature = "sha256=" + hash_object.hexdigest()

        response = client.post(
            "/webhooks/github",
            headers={
                "X-GitHub-Event": "issues",
                "X-Hub-Signature-256": signature,
            },
            content=payload_bytes,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "accepted", "event": "issues"}
        )
        del os.environ["GITHUB_WEBHOOK_SECRET"]

    def test_missing_secret_in_production(self):
        # Ensure ENVIRONMENT is not 'development'
        os.environ["ENVIRONMENT"] = "production"

        # Ensure GITHUB_WEBHOOK_SECRET is not set
        if "GITHUB_WEBHOOK_SECRET" in os.environ:
            del os.environ["GITHUB_WEBHOOK_SECRET"]

        payload = {"action": "opened", "issue": {"number": 456}}
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "issues"},
            json=payload,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Invalid signature"})


if __name__ == "__main__":
    unittest.main()
