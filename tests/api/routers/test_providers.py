import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization


@pytest.fixture
def test_client():
    return TestClient(app)


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
    assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"


@pytest.fixture
def mock_provider_manager(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("gossipmesh.api.routers.providers.ProviderManager", lambda: mock)
    return mock


def test_register_provider_success(test_client, mock_current_user, mock_provider_manager):
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        UserOrganization(user_id=1, organization_id=1, role="developer"),
        None,
    ]
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post(
        "/api/v1/providers/register?organization_id=1", json={"name": "test-provider", "api_key": "secret"}
    )

    assert response.status_code == 201
    assert response.json()["status"] == "success"


def test_health_check_unauthorized(test_client, mock_current_user):
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.get("/api/v1/providers/health?organization_id=1")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_ERROR"
