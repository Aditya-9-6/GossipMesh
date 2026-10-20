from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.service_account import APIKey, ServiceAccount

client = TestClient(app)


def mock_get_scim_token():
    return APIKey(id=1, service_account_id=1, prefix="prefix")


def test_get_scim_token_missing_header():
    app.dependency_overrides.clear()
    response = client.get("/api/v1/scim/v2/1/Users")
    assert response.status_code == 401
    assert "Bearer token required" in response.json()["error"]["message"]


def test_list_users_empty():
    mock_db = MagicMock()
    # It appears app.dependency_overrides is misbehaving if the function is not imported exactly as deps.get_scim_token
    # In some fastapi structures, you must override it via the router's imported version, e.g. scim.get_scim_token. Let's just bypass auth for the test client by monkeypatching the function in deps itself to always return true, or simply creating a valid headers.

    app.dependency_overrides.clear()
    app.dependency_overrides[deps.get_db] = lambda: mock_db
    app.dependency_overrides[deps.get_scim_token] = mock_get_scim_token

    mock_db.query.return_value.filter.return_value.first.side_effect = [ServiceAccount(id=1, organization_id=1)]
    mock_db.query.return_value.join.return_value.filter.return_value.count.return_value = 0
    mock_db.query.return_value.join.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []

    # Since dependency_overrides keeps failing, let's use a real token mock if it continues to fail.
    response = client.get("/api/v1/scim/v2/1/Users")
    assert response.status_code == 200


def test_create_user():
    mock_db = MagicMock()
    app.dependency_overrides = {
        deps.get_db: lambda: mock_db,
        deps.get_scim_token: mock_get_scim_token,
    }
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        ServiceAccount(id=1, organization_id=1),  # Account check
        None,  # User check
        None,  # User_Org check
    ]

    def side_effect(obj):
        if isinstance(obj, User):
            obj.id = 1
        if isinstance(obj, UserOrganization):
            obj.user_id = 1
            obj.organization_id = 1
            obj.is_suspended = False

    mock_db.add.side_effect = side_effect

    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "test@example.com",
        "emails": [{"value": "test@example.com"}],
        "active": True,
    }
    response = client.post("/api/v1/scim/v2/1/Users", json=payload)
    assert response.status_code == 201


def test_get_user():
    mock_db = MagicMock()
    app.dependency_overrides = {
        deps.get_db: lambda: mock_db,
        deps.get_scim_token: mock_get_scim_token,
    }
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        ServiceAccount(id=1, organization_id=1),
        UserOrganization(user_id=1, organization_id=1, is_suspended=False),
        User(id=1, email="test@example.com", is_active=True),
    ]
    response = client.get("/api/v1/scim/v2/1/Users/1")
    assert response.status_code == 200


def test_patch_user():
    mock_db = MagicMock()
    app.dependency_overrides = {
        deps.get_db: lambda: mock_db,
        deps.get_scim_token: mock_get_scim_token,
    }
    user_org = UserOrganization(user_id=1, organization_id=1, is_suspended=False)
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        ServiceAccount(id=1, organization_id=1),
        user_org,
        User(id=1, email="test@example.com", is_active=True),
    ]
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "active", "value": False}],
    }
    response = client.patch("/api/v1/scim/v2/1/Users/1", json=payload)
    assert response.status_code == 200


def test_delete_user():
    mock_db = MagicMock()
    app.dependency_overrides = {
        deps.get_db: lambda: mock_db,
        deps.get_scim_token: mock_get_scim_token,
    }
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        ServiceAccount(id=1, organization_id=1),
        UserOrganization(user_id=1, organization_id=1),
    ]
    response = client.delete("/api/v1/scim/v2/1/Users/1")
    assert response.status_code == 204


def test_list_groups():
    mock_db = MagicMock()
    app.dependency_overrides = {
        deps.get_db: lambda: mock_db,
        deps.get_scim_token: mock_get_scim_token,
    }
    mock_db.query.return_value.filter.return_value.first.side_effect = [ServiceAccount(id=1, organization_id=1)]
    response = client.get("/api/v1/scim/v2/1/Groups")
    assert response.status_code == 200
