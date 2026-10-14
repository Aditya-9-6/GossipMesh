import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.service_account import ServiceAccount, APIKey
from gossipmesh.api import deps
from gossipmesh.api.main import app


# Create dummy verify function to avoid passlib bcrypt issues in tests
def dummy_verify(plain, hashed):
    return hashed == f"hashed_{plain}"

class TestServiceAccounts(unittest.TestCase):
    def setUp(self):
        self.test_client = TestClient(app)
        self.mock_db_session = MagicMock()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_create_service_account(self):
        user = User(id=1, email="test@example.com")
        org = Organization(id=1, name="Test Org")
        user_org = UserOrganization(user_id=1, organization_id=1)

        self.mock_db_session.query.return_value.filter.return_value.first.return_value = user_org

        # Need to override dependencies to use the mock db and mock current user
        app.dependency_overrides[deps.get_current_user] = lambda: user
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db_session

        def side_effect(obj):
            if isinstance(obj, ServiceAccount):
                obj.id = 1
            return None

        self.mock_db_session.add.return_value = None
        self.mock_db_session.commit.return_value = None
        self.mock_db_session.refresh.side_effect = side_effect

        response = self.test_client.post(
            "/api/v1/service-accounts/",
            json={"organization_id": 1, "name": "CI Bot", "description": "Used for CI/CD"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "CI Bot")
        self.assertEqual(data["description"], "Used for CI/CD")
        self.assertEqual(data["organization_id"], 1)

    @patch("gossipmesh.api.routers.service_accounts.get_password_hash", side_effect=lambda x: f"hashed_{x}")
    def test_create_api_key(self, mock_get_password_hash):
        user = User(id=1, email="test@example.com")
        account = ServiceAccount(id=1, organization_id=1, name="CI Bot")
        user_org = UserOrganization(user_id=1, organization_id=1)

        def mock_query_first(model):
            if model == ServiceAccount:
                return account
            elif model == UserOrganization:
                return user_org
            return None

        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.side_effect = [account, user_org]
        query_mock.filter.return_value = filter_mock
        self.mock_db_session.query.return_value = query_mock

        app.dependency_overrides[deps.get_current_user] = lambda: user
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db_session

        def side_effect(obj):
            if isinstance(obj, APIKey):
                obj.id = 1
                obj.created_at = datetime.now(timezone.utc)
            return None

        self.mock_db_session.refresh.side_effect = side_effect

        response = self.test_client.post(
            "/api/v1/service-accounts/1/keys",
            json={"name": "Deploy Key", "scopes": ["read", "write"], "expires_in_days": 30}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Deploy Key")
        self.assertIn("key", data)
        self.assertTrue(data["key"].startswith("gm_"))
        self.assertIn("prefix", data)
        self.assertTrue(data["key"].startswith(data["prefix"]))
        self.assertEqual(data["scopes"], ["read", "write"])

        # Asserting that hashed_key isn't returned
        self.assertNotIn("hashed_key", data)

        # Verify hashed key
        args_list = self.mock_db_session.add.call_args_list
        api_key_obj = [call.args[0] for call in args_list if isinstance(call.args[0], APIKey)][0]
        self.assertEqual(api_key_obj.hashed_key, f"hashed_{data['key']}")

    def test_list_api_keys_does_not_return_raw_key(self):
        user = User(id=1, email="test@example.com")
        account = ServiceAccount(id=1, organization_id=1, name="CI Bot")
        user_org = UserOrganization(user_id=1, organization_id=1)
        api_key = APIKey(
            id=1,
            service_account_id=1,
            name="Deploy Key",
            prefix="gm_abc123",
            hashed_key="hashed",
            scopes=["read"],
            is_revoked=False,
            created_at=datetime.now(timezone.utc)
        )

        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.side_effect = [account, user_org]
        filter_mock.all.return_value = [api_key]
        query_mock.filter.return_value = filter_mock
        self.mock_db_session.query.return_value = query_mock

        app.dependency_overrides[deps.get_current_user] = lambda: user
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db_session

        response = self.test_client.get("/api/v1/service-accounts/1/keys")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Deploy Key")
        self.assertEqual(data[0]["prefix"], "gm_abc123")
        self.assertNotIn("key", data[0]) # The raw key should not be returned here
        self.assertNotIn("hashed_key", data[0]) # Nor the hashed key

    def test_revoke_api_key(self):
        user = User(id=1, email="test@example.com")
        account = ServiceAccount(id=1, organization_id=1, name="CI Bot")
        user_org = UserOrganization(user_id=1, organization_id=1)
        api_key = APIKey(id=1, service_account_id=1, prefix="gm_abc123", is_revoked=False)

        query_mock = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.side_effect = [api_key, account, user_org]
        query_mock.filter.return_value = filter_mock
        self.mock_db_session.query.return_value = query_mock

        app.dependency_overrides[deps.get_current_user] = lambda: user
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db_session

        response = self.test_client.delete("/api/v1/service-accounts/keys/1")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(api_key.is_revoked)

if __name__ == '__main__':
    unittest.main()
