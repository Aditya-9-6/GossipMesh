import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import tests # Initialize dummy environment variables
from gossipmesh.api import app
from gossipmesh.api.deps import get_db, get_current_user
from gossipmesh.models.user import User
from gossipmesh.models.webhooks import WebhookEvent
import os
import hashlib
import hmac
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from gossipmesh.models.base import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

class TestWebhooks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.original_env = os.environ.get("ENVIRONMENT")
        os.environ["ENVIRONMENT"] = "development"
        # Clear db
        db = TestingSessionLocal()
        db.query(WebhookEvent).delete()
        db.query(User).delete()
        db.commit()
        db.close()

    def tearDown(self):
        if self.original_env is not None:
            os.environ["ENVIRONMENT"] = self.original_env
        else:
            del os.environ["ENVIRONMENT"]
        app.dependency_overrides = {get_db: override_get_db} # Reset other overrides

    def test_missing_event_header(self):
        response = client.post("/webhooks/github", json={})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["error"]["message"], "Missing X-GitHub-Event header"
        )

    @patch("gossipmesh.jobs.pr_review.PRReviewJob.execute")
    def test_pull_request_event(self, mock_execute):
        payload = {"action": "opened", "pull_request": {"number": 123}}
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-1"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"status": "accepted", "event": "pull_request"}
        )

        # Verify persistence
        db = TestingSessionLocal()
        event = db.query(WebhookEvent).filter(WebhookEvent.delivery_id == "delivery-1").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.status, "processed")
        db.close()

    @patch("gossipmesh.workflows.issue_solver.IssueSolverWorkflow.execute")
    def test_webhook_idempotency(self, mock_execute):
        payload = {"action": "opened", "issue": {"number": 456}}
        headers = {"X-GitHub-Event": "issues", "X-GitHub-Delivery": "delivery-2"}

        # First call
        response1 = client.post("/webhooks/github", headers=headers, json=payload)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()["status"], "accepted")

        # Second call
        response2 = client.post("/webhooks/github", headers=headers, json=payload)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()["status"], "already_processed")

        db = TestingSessionLocal()
        count = db.query(WebhookEvent).filter(WebhookEvent.delivery_id == "delivery-2").count()
        self.assertEqual(count, 1) # No duplicate side effect
        db.close()

    @patch("gossipmesh.workflows.issue_solver.IssueSolverWorkflow.execute")
    def test_replay_endpoint_admin_only(self, mock_execute):
        # Create user and event
        db = TestingSessionLocal()
        user = User(email="admin@test.com", is_active=True, is_superuser=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        non_admin_user = User(email="user@test.com", is_active=True, is_superuser=False)
        db.add(non_admin_user)
        db.commit()
        db.refresh(non_admin_user)
        non_admin_user_id = non_admin_user.id

        event = WebhookEvent(delivery_id="delivery-3", event="issues", payload={"action": "opened"}, status="processed")
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
        db.close()

        # Try with non-admin
        def override_get_current_user_non_admin():
            return User(id=non_admin_user_id, email="user@test.com", is_active=True, is_superuser=False)

        app.dependency_overrides[get_current_user] = override_get_current_user_non_admin
        response = client.post(f"/webhooks/github/replay/{event_id}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["message"], "Administrator privileges required")

        # Try with admin
        def override_get_current_user_admin():
            return User(id=user_id, email="admin@test.com", is_active=True, is_superuser=True)

        app.dependency_overrides[get_current_user] = override_get_current_user_admin
        response = client.post(f"/webhooks/github/replay/{event_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "replayed")

        # Verify replayed logic
        db = TestingSessionLocal()
        replayed_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        self.assertIsNotNone(replayed_event.replayed_at)
        self.assertEqual(replayed_event.replayed_by, user_id)
        db.close()

if __name__ == "__main__":
    unittest.main()
