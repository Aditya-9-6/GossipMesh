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

    @patch('gossipmesh.api.routers.auth.verify_password')
    def test_login_creates_session_and_refresh_token(self, mock_verify):
        mock_verify.return_value = True
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
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_refresh_token_rotation_and_reuse_detection(self):
        from gossipmesh.models.session import UserSession, RefreshToken
        from datetime import datetime, timedelta, timezone
        from gossipmesh.core.security import create_refresh_token
        import uuid

        # Mock session and tokens
        session_id = 1
        user_id = 1
        jti = str(uuid.uuid4())

        mock_session = UserSession(id=session_id, user_id=user_id, is_active=True, refresh_tokens=[])
        mock_refresh_token = RefreshToken(id=1, session_id=session_id, jti=jti, is_revoked=False, expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        mock_session.refresh_tokens.append(mock_refresh_token)

        # Configure mock DB behavior to return our specific models when queried
        def mock_query_side_effect(*args, **kwargs):
            mock_query = MagicMock()
            if args[0] == RefreshToken:
                mock_query.filter.return_value.first.return_value = mock_refresh_token
            elif args[0] == UserSession:
                mock_query.filter.return_value.first.return_value = mock_session
            elif args[0] == User:
                mock_query.filter.return_value.first.return_value = User(id=1, email="test@example.com", is_active=True)
            return mock_query

        self.mock_db.query.side_effect = mock_query_side_effect

        # Generate valid JWT string for testing
        token_str = create_refresh_token(subject=user_id, session_id=session_id, jti=jti)

        # Test successful rotation
        response = client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": token_str}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

        # Test reuse detection (token is now revoked)
        mock_refresh_token.is_revoked = True

        response_reuse = client.post(
            f"{settings.API_V1_STR}/auth/refresh",
            json={"refresh_token": token_str}
        )

        self.assertEqual(response_reuse.status_code, 401)
        self.assertEqual(response_reuse.json()["error"]["message"], "Token has been revoked, session terminated")
        self.assertFalse(mock_session.is_active)

    def test_session_revocation(self):
        from gossipmesh.models.session import UserSession, RefreshToken
        from datetime import datetime, timezone

        # Override get_current_user dependency
        mock_user = User(id=1, email="test@example.com", is_active=True)
        app.dependency_overrides[deps.get_current_user] = lambda: mock_user

        session_id = 1
        mock_session = UserSession(
            id=session_id,
            user_id=mock_user.id,
            is_active=True,
            ip_address="127.0.0.1",
            user_agent="TestAgent",
            created_at=datetime.now(timezone.utc),
            last_active_at=datetime.now(timezone.utc),
            refresh_tokens=[RefreshToken(id=1, is_revoked=False)]
        )

        # Mock DB behavior
        def mock_query_side_effect(*args, **kwargs):
            mock_query = MagicMock()
            if args[0] == UserSession:
                # Handle filter for get_sessions (.all()) and revoke_session (.first())
                mock_query.filter.return_value.all.return_value = [mock_session]
                mock_query.filter.return_value.first.return_value = mock_session
            return mock_query

        self.mock_db.query.side_effect = mock_query_side_effect

        # Test listing sessions
        response_list = client.get(f"{settings.API_V1_STR}/auth/sessions")
        self.assertEqual(response_list.status_code, 200)
        sessions = response_list.json()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["id"], session_id)

        # Test revoking session
        response_revoke = client.delete(f"{settings.API_V1_STR}/auth/sessions/{session_id}")
        self.assertEqual(response_revoke.status_code, 204)

        # Verify session and tokens were revoked
        self.assertFalse(mock_session.is_active)
        self.assertTrue(mock_session.refresh_tokens[0].is_revoked)

if __name__ == '__main__':
    unittest.main()
