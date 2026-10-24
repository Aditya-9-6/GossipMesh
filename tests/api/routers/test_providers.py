import pytest
from unittest.mock import MagicMock
from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.user import User


@pytest.fixture
def mock_current_user():
    user = User(id=1, email="test@example.com", hashed_password="hashed")
    app.dependency_overrides[deps.get_current_user] = lambda: user
    yield user
    app.dependency_overrides.clear()


def test_register_provider_unauthorized(test_client, mock_current_user):
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session
    response = test_client.post(
        "/api/v1/providers/register?organization_id=1", json={"name": "test-provider", "api_key": "secret"}
    )
    assert response.status_code == 403
