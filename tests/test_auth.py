import tests  # Initialize env vars
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.core.config import settings

client = TestClient(app)

class TestAuth(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock(spec=Session)

        # Override dependency
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch('gossipmesh.api.routers.auth.verify_password')
    def test_login_success(self, mock_verify):
        mock_verify.return_value = True
        # Setup mock user
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="mocked_hash",
            is_active=True
        )
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        response = client.post(
            f"{settings.API_V1_STR}/auth/login/access-token",
            data={"username": "test@example.com", "password": "password123"}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        mock_verify.assert_called_once_with("password123", "mocked_hash")

    @patch('gossipmesh.api.routers.auth.verify_password')
    def test_login_incorrect_password(self, mock_verify):
        mock_verify.return_value = False
        # Setup mock user
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="mocked_hash",
            is_active=True
        )
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        response = client.post(
            f"{settings.API_V1_STR}/auth/login/access-token",
            data={"username": "test@example.com", "password": "wrongpassword"}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "Incorrect email or password")
        mock_verify.assert_called_once_with("wrongpassword", "mocked_hash")

    def test_login_user_not_found(self):
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post(
            f"{settings.API_V1_STR}/auth/login/access-token",
            data={"username": "nonexistent@example.com", "password": "password123"}
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "Incorrect email or password")

    @patch('gossipmesh.api.routers.auth.verify_password')
    def test_login_inactive_user(self, mock_verify):
        mock_verify.return_value = True
        # Setup mock inactive user
        mock_user = User(
            id=1,
            email="test@example.com",
            hashed_password="mocked_hash",
            is_active=False
        )
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        response = client.post(
            f"{settings.API_V1_STR}/auth/login/access-token",
            data={"username": "test@example.com", "password": "password123"}
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["message"], "Inactive user")
        mock_verify.assert_called_once_with("password123", "mocked_hash")


    @patch('gossipmesh.api.routers.auth.httpx.Client.get')
    @patch('gossipmesh.api.routers.auth.redis_client')
    def test_oidc_login(self, mock_redis, mock_get):
        settings.OIDC_DISCOVERY_URL = "https://provider.com/.well-known/openid-configuration"
        settings.OIDC_CLIENT_ID = "test-client"
        settings.OIDC_REDIRECT_URI = "https://app.com/callback"

        mock_discovery_response = MagicMock()
        mock_discovery_response.json.return_value = {
            "authorization_endpoint": "https://provider.com/auth"
        }
        mock_get.return_value = mock_discovery_response

        response = client.get(f"{settings.API_V1_STR}/auth/oidc/login", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertIn("https://provider.com/auth", response.headers["location"])
        self.assertIn("response_type=code", response.headers["location"])
        self.assertIn("code_challenge_method=S256", response.headers["location"])

        mock_redis.setex.assert_called_once()

    @patch('gossipmesh.api.routers.auth.jwt.decode')
    @patch('gossipmesh.api.routers.auth.PyJWKClient')
    @patch('gossipmesh.api.routers.auth.httpx.Client.post')
    @patch('gossipmesh.api.routers.auth.httpx.Client.get')
    @patch('gossipmesh.api.routers.auth.redis_client')
    def test_oidc_callback(self, mock_redis, mock_get, mock_post, mock_jwks, mock_jwt_decode):
        settings.OIDC_DISCOVERY_URL = "https://provider.com/.well-known/openid-configuration"
        settings.OIDC_CLIENT_ID = "test-client"
        settings.OIDC_CLIENT_SECRET = "test-secret"
        settings.OIDC_REDIRECT_URI = "https://app.com/callback"

        mock_redis.get.return_value = "test-nonce:test-verifier"

        mock_discovery_response = MagicMock()
        mock_discovery_response.json.return_value = {
            "token_endpoint": "https://provider.com/token",
            "jwks_uri": "https://provider.com/jwks",
            "issuer": "https://provider.com"
        }
        mock_get.return_value = mock_discovery_response

        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            "access_token": "mock-access",
            "id_token": "mock-id",
            "refresh_token": "mock-refresh"
        }
        mock_post.return_value = mock_token_response

        mock_jwks.return_value.get_signing_key_from_jwt.return_value.key = "mock-key"

        mock_jwt_decode.return_value = {
            "nonce": "test-nonce",
            "email": "testoidc@example.com",
            "sub": "user123",
            "iss": "https://provider.com",
            "groups": ["engineering", "admin"]
        }

        # Mock DB logic
        from gossipmesh.models.user import User
        from gossipmesh.models.organization import Organization
        from gossipmesh.models.audit import AuditEvent

        mock_user = User(id=1, email="testoidc@example.com")
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            None, # First query: User
            None, # Second query: UserOIDCCredential
            Organization(id=1, name="engineering"), # Third query: Organization engineering
            None, # Fourth query: UserOrganization engineering
            None, # Fifth query: Organization admin
        ]

        # intercept add to give objects an ID
        def mock_add(obj):
             if isinstance(obj, User):
                 obj.id = 1

        self.mock_db.add.side_effect = mock_add

        response = client.get(
            f"{settings.API_V1_STR}/auth/oidc/callback?state=test-state&code=test-code"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())
        self.assertEqual(response.json()["token_type"], "bearer")
        self.mock_db.add.assert_called()

if __name__ == '__main__':
    unittest.main()
