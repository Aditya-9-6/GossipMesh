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
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

        self.patcher_verify = patch('gossipmesh.api.routers.auth.verify_password')
        self.mock_verify = self.patcher_verify.start()

        self.patcher_redis = patch('gossipmesh.api.routers.auth.redis_client')
        self.mock_redis = self.patcher_redis.start()
        self.mock_redis.exists.return_value = False
        self.mock_redis.incr.return_value = 1

        self.patcher_dummy = patch('gossipmesh.api.routers.auth.dummy_verify')
        self.mock_dummy = self.patcher_dummy.start()

        self.patcher_hash = patch('gossipmesh.api.routers.auth.get_password_hash')
        self.mock_get_hash = self.patcher_hash.start()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.patcher_verify.stop()
        self.patcher_redis.stop()
        self.patcher_dummy.stop()
        self.patcher_hash.stop()

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



    def test_password_strength_validation(self):
        from gossipmesh.core.security import validate_password_strength
        with self.assertRaises(ValueError):
            validate_password_strength("Short1!")
        with self.assertRaises(ValueError):
            validate_password_strength("lowercase1!")
        with self.assertRaises(ValueError):
            validate_password_strength("UPPERCASE1!")
        with self.assertRaises(ValueError):
            validate_password_strength("NoDigitsHere!")
        with self.assertRaises(ValueError):
            validate_password_strength("NoSpecialChar1")
        validate_password_strength("ValidPassword1!")

    def test_login_throttling_and_lockout(self):
        self.mock_verify.return_value = False
        self.mock_redis.exists.return_value = False
        self.mock_redis.incr.return_value = 5 # Trigger lockout

        mock_user = User(id=1, email="test@example.com", hashed_password="mocked_hash", is_active=True)
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        response = client.post(
            f"{settings.API_V1_STR}/auth/login/access-token",
            data={"username": "test@example.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 401)
        self.mock_redis.setex.assert_called_with("lockout:test@example.com", 300, "1")

        self.mock_redis.exists.return_value = True
        response = client.post(
            f"{settings.API_V1_STR}/auth/login/access-token",
            data={"username": "test@example.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["message"], "Account temporarily locked out. Try again later.")

if __name__ == '__main__':
    unittest.main()
