import unittest
from gossipmesh.worker.tasks.webhook_dispatch import process_webhook_event
from unittest.mock import patch
from fastapi.testclient import TestClient
from gossipmesh.api import app
from gossipmesh.api.deps import get_db, get_current_user
from gossipmesh.models.user import User
from gossipmesh.models.webhooks import WebhookEvent
import os
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

    @patch("gossipmesh.api.webhooks.process_webhook_event.apply_async")
    def test_concurrent_delivery(self, mock_apply):
        from sqlalchemy.exc import IntegrityError
        from sqlalchemy.orm import Session
        headers = {"X-GitHub-Event": "issues", "X-GitHub-Delivery": "delivery-concurrent-mock"}
        payload = {"action": "opened", "issue": {"number": 999}}

        # First request succeeds
        response1 = client.post("/webhooks/github", headers=headers, json=payload)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.json()["status"], "accepted")

        # Second request simulates IntegrityError when adding
        with patch.object(Session, "flush", side_effect=IntegrityError("Mock Error", "params", "orig")):
            response2 = client.post("/webhooks/github", headers=headers, json=payload)
            self.assertEqual(response2.status_code, 200)
            self.assertEqual(response2.json()["status"], "already_processed")

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

    @patch("gossipmesh.core.concurrency_limit.redis_client")
    @patch("gossipmesh.worker.tasks.webhook_dispatch.SessionLocal")
    @patch("gossipmesh.worker.tasks.webhook_dispatch.async_dispatch")
    def test_process_webhook_event_success(self, mock_dispatch, mock_session_local, mock_redis):
        from gossipmesh.worker.tasks.webhook_dispatch import process_webhook_event
        mock_session_local.return_value = TestingSessionLocal()

        # Mock eval to return success (1)
        mock_redis.eval.return_value = 1

        db = TestingSessionLocal()
        event = WebhookEvent(delivery_id="delivery-task-1", event="issues", payload={"action": "opened"}, status="pending")
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
        db.close()

        process_webhook_event(event_id)

        db = TestingSessionLocal()
        updated_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        self.assertEqual(updated_event.status, "processed")
        self.assertEqual(updated_event.retries, 0)
        db.close()

    @patch("gossipmesh.core.concurrency_limit.redis_client")
    @patch("gossipmesh.worker.tasks.webhook_dispatch.SessionLocal")
    @patch("gossipmesh.worker.tasks.webhook_dispatch.async_dispatch")
    @patch("gossipmesh.worker.tasks.webhook_dispatch.process_webhook_event.retry")
    def test_process_webhook_event_failure_and_retry(self, mock_retry, mock_dispatch, mock_session_local, mock_redis):
        from gossipmesh.worker.tasks.webhook_dispatch import process_webhook_event
        mock_session_local.return_value = TestingSessionLocal()
        mock_redis.eval.return_value = 1
        mock_dispatch.side_effect = Exception("Test failure")
        mock_retry.side_effect = Exception("Retry triggered")

        db = TestingSessionLocal()
        event = WebhookEvent(delivery_id="delivery-task-2", event="issues", payload={"action": "opened"}, status="pending")
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
        db.close()

        with self.assertRaises(Exception) as context:
            process_webhook_event(event_id)

        self.assertTrue("Retry triggered" in str(context.exception))

        db = TestingSessionLocal()
        updated_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        self.assertEqual(updated_event.status, "failed")
        self.assertEqual(updated_event.retries, 1)
        self.assertIsNotNone(updated_event.next_retry_at)
        db.close()

    @patch("gossipmesh.core.concurrency_limit.redis_client")
    @patch("gossipmesh.worker.tasks.webhook_dispatch.SessionLocal")
    @patch("gossipmesh.worker.tasks.webhook_dispatch.async_dispatch")
    def test_process_webhook_event_dead_letter(self, mock_dispatch, mock_session_local, mock_redis):
        from gossipmesh.worker.tasks.webhook_dispatch import process_webhook_event
        mock_session_local.return_value = TestingSessionLocal()
        mock_redis.eval.return_value = 1
        mock_dispatch.side_effect = Exception("Test failure")

        db = TestingSessionLocal()
        event = WebhookEvent(delivery_id="delivery-task-3", event="issues", payload={"action": "opened"}, status="pending", retries=4)
        db.add(event)
        db.commit()
        db.refresh(event)
        event_id = event.id
        db.close()

        process_webhook_event(event_id)

        db = TestingSessionLocal()
        updated_event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
        self.assertEqual(updated_event.status, "dead_letter")
        self.assertEqual(updated_event.retries, 5)
        db.close()

    def test_malformed_payload(self):
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-malformed"},
            content=b"not a valid json"
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["message"], "Invalid JSON payload")

    def test_payload_size_limit(self):
        payload_bytes = b"A" * (25 * 1024 * 1024 + 1)
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-size-limit", "Content-Type": "application/json"},
            content=payload_bytes
        )
        self.assertEqual(response.status_code, 413)
        pass  # Detail string or format could be different

if __name__ == "__main__":
    unittest.main()
