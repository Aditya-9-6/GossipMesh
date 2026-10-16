import unittest
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

    def test_installation_created_event(self):
        payload = {
            "action": "created",
            "installation": {
                "id": 789,
                "account": {"login": "test-org", "type": "Organization", "id": 1234},
                "repository_selection": "selected",
                "permissions": {"issues": "write"}
            }
        }
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "installation", "X-GitHub-Delivery": "delivery-created"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)

        db = TestingSessionLocal()
        from gossipmesh.models.repository import GithubAppInstallation
        from gossipmesh.models.audit import AuditEvent
        inst = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == 789).first()
        self.assertIsNotNone(inst)
        self.assertEqual(inst.account_name, "test-org")
        self.assertEqual(inst.target_type, "Organization")
        self.assertEqual(inst.repository_selection, "selected")

        audit = db.query(AuditEvent).filter(AuditEvent.action == "installation.created").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.details["installation_id"], 789)
        db.close()

    def test_installation_deleted_event(self):
        db = TestingSessionLocal()
        from gossipmesh.models.repository import GithubAppInstallation
        from gossipmesh.models.audit import AuditEvent
        inst = GithubAppInstallation(
            installation_id=789, account_name="test", target_type="User",
            target_id=1, repository_selection="all", permissions={}
        )
        db.add(inst)
        db.commit()
        db.close()

        payload = {"action": "deleted", "installation": {"id": 789}}
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "installation", "X-GitHub-Delivery": "delivery-deleted"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)

        db = TestingSessionLocal()
        inst = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == 789).first()
        self.assertIsNone(inst)
        audit = db.query(AuditEvent).filter(AuditEvent.action == "installation.deleted").first()
        self.assertIsNotNone(audit)
        db.close()

    def test_installation_suspend_event(self):
        db = TestingSessionLocal()
        from gossipmesh.models.repository import GithubAppInstallation
        from gossipmesh.models.audit import AuditEvent
        inst = GithubAppInstallation(
            installation_id=789, account_name="test", target_type="User",
            target_id=1, repository_selection="all", permissions={}
        )
        db.add(inst)
        db.commit()
        db.close()

        payload = {"action": "suspend", "installation": {"id": 789}, "sender": {"login": "admin-user"}}
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "installation", "X-GitHub-Delivery": "delivery-suspend"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)

        db = TestingSessionLocal()
        inst = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == 789).first()
        self.assertIsNotNone(inst.suspended_at)
        self.assertEqual(inst.suspended_by, "admin-user")
        audit = db.query(AuditEvent).filter(AuditEvent.action == "installation.suspended").first()
        self.assertIsNotNone(audit)
        db.close()

    def test_installation_unsuspend_event(self):
        db = TestingSessionLocal()
        from datetime import datetime, timezone
        from gossipmesh.models.repository import GithubAppInstallation
        from gossipmesh.models.audit import AuditEvent
        inst = GithubAppInstallation(
            installation_id=789, account_name="test", target_type="User",
            target_id=1, repository_selection="all", permissions={},
            suspended_at=datetime.now(timezone.utc), suspended_by="admin-user"
        )
        db.add(inst)
        db.commit()
        db.close()

        payload = {"action": "unsuspend", "installation": {"id": 789}}
        response = client.post(
            "/webhooks/github",
            headers={"X-GitHub-Event": "installation", "X-GitHub-Delivery": "delivery-unsuspend"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)

        db = TestingSessionLocal()
        inst = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == 789).first()
        self.assertIsNone(inst.suspended_at)
        self.assertIsNone(inst.suspended_by)
        audit = db.query(AuditEvent).filter(AuditEvent.action == "installation.unsuspended").first()
        self.assertIsNotNone(audit)
        db.close()
