import unittest

from fastapi.testclient import TestClient

from gossipmesh.api import deps
from gossipmesh.api.main import app
from gossipmesh.models.user import User

client = TestClient(app)


class TestUsersRouter(unittest.TestCase):
    def setUp(self):
        # Ensure dependencies are clean before each test
        app.dependency_overrides = {}

    def test_read_user_me_authenticated(self):
        # Create a mock user
        mock_user = User(id=1, email="test@example.com", is_active=True)

        # Override the dependency to return the mock user
        def override_get_current_user():
            return mock_user

        app.dependency_overrides[deps.get_current_user] = override_get_current_user

        # Make the request
        response = client.get("/api/v1/users/me")

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": 1, "email": "test@example.com", "is_active": True},
        )

    def test_read_user_me_unauthenticated(self):
        # Make the request without overriding the dependency or providing a token
        response = client.get("/api/v1/users/me")

        # The endpoint should return 401 Unauthorized since OAuth2PasswordBearer
        # normally returns a 401 when a token is not provided.
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Not authenticated"})


if __name__ == "__main__":
    unittest.main()
