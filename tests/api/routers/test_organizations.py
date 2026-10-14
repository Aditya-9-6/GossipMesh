from unittest.mock import MagicMock

import pytest

from gossipmesh.api import deps
from gossipmesh.api.main import app
from gossipmesh.models.organization import Organization
from gossipmesh.models.user import User


@pytest.fixture
def mock_current_user():
    user = User(id=1, email="test@example.com", hashed_password="hashed")
    app.dependency_overrides[deps.get_current_user] = lambda: user
    yield user
    app.dependency_overrides.clear()

@pytest.fixture
def mock_db():
    mock = MagicMock()
    app.dependency_overrides[deps.get_db] = lambda: mock
    yield mock
    app.dependency_overrides.pop(deps.get_db, None)

def test_read_organizations_me(test_client, mock_db, mock_current_user):
    mock_org = Organization(id=1, name="My Org")
    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_org]

    response = test_client.get("/api/v1/organizations/me")

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "name": "My Org"}]
