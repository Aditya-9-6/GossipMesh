import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db_session():
    return MagicMock()


from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, UserOrganization, OrganizationInvitation
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository
from gossipmesh.models.audit import AuditEvent


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


@pytest.fixture
def test_client():
    return TestClient(app)


def test_create_organization(test_client, mock_db, mock_current_user):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    def side_effect(obj):
        if isinstance(obj, Organization):
            obj.id = 1
        if isinstance(obj, UserOrganization):
            pass

    mock_db.add.side_effect = side_effect

    response = test_client.post("/api/v1/organizations/", json={"name": "New Org"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "New Org"}
    assert mock_db.add.call_count == 3


def test_create_organization_exists(test_client, mock_db, mock_current_user):
    mock_db.query.return_value.filter.return_value.first.return_value = Organization(id=1, name="Existing")

    response = test_client.post("/api/v1/organizations/", json={"name": "Existing"})
    assert response.status_code == 400


def test_create_invitation(test_client, mock_db, mock_current_user):
    mock_db.query.return_value.filter.return_value.first.return_value = UserOrganization(
        role="organization_admin", is_suspended=False
    )

    response = test_client.post(
        "/api/v1/organizations/1/invitations", json={"email": "invite@example.com", "role": "developer"}
    )

    assert response.status_code == 200
    assert "token" in response.json()


def test_create_invitation_unauthorized(test_client, mock_db, mock_current_user):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = test_client.post(
        "/api/v1/organizations/1/invitations", json={"email": "invite@example.com", "role": "developer"}
    )

    assert response.status_code == 403


def test_accept_invitation(test_client, mock_db, mock_current_user):
    mock_invitation = OrganizationInvitation(
        id=1, email="invite@example.com", token="valid_token", organization_id=1, role="developer"
    )

    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_invitation, None]

    response = test_client.post("/api/v1/organizations/invitations/valid_token/accept")

    assert response.status_code == 200
    assert mock_db.add.call_count == 2
    assert mock_db.delete.call_count == 1


def test_assign_role(test_client, mock_db, mock_current_user):
    mock_admin_check = UserOrganization(role="organization_admin", is_suspended=False)
    mock_user_org = UserOrganization(organization_id=1, user_id=2, role="developer")
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_admin_check, mock_user_org]

    response = test_client.patch("/api/v1/organizations/1/members/2/role", json={"role": "organization_admin"})

    assert response.status_code == 200
    assert mock_user_org.role == "organization_admin"


def test_create_project(test_client, mock_db, mock_current_user):
    mock_db.query.return_value.filter.return_value.first.return_value = UserOrganization(
        role="organization_admin", is_suspended=False
    )

    def side_effect(obj):
        if isinstance(obj, Project):
            obj.id = 1

    mock_db.add.side_effect = side_effect

    response = test_client.post("/api/v1/organizations/1/projects", json={"name": "New Project", "description": "Desc"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "New Project", "description": "Desc"}


def test_connect_repository(test_client, mock_db, mock_current_user):
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        UserOrganization(role="organization_admin", is_suspended=False),
        None,
    ]

    def side_effect(obj):
        if isinstance(obj, Repository):
            obj.id = 1

    mock_db.add.side_effect = side_effect

    response = test_client.post(
        "/api/v1/organizations/1/repositories",
        json={"github_id": 123, "name": "repo", "full_name": "org/repo", "default_branch": "main"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_remove_member(test_client, mock_db, mock_current_user):
    mock_admin_check = UserOrganization(role="organization_admin", is_suspended=False)
    mock_user_org = UserOrganization(organization_id=1, user_id=2, role="developer")
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_admin_check, mock_user_org]

    response = test_client.delete("/api/v1/organizations/1/members/2")

    assert response.status_code == 200
    assert mock_db.delete.call_count == 1


def test_suspend_member(test_client, mock_db, mock_current_user):
    mock_admin_check = UserOrganization(role="organization_admin", is_suspended=False)
    mock_user_org = UserOrganization(organization_id=1, user_id=2, role="developer", is_suspended=False)
    mock_db.query.return_value.filter.return_value.first.side_effect = [mock_admin_check, mock_user_org]

    response = test_client.patch("/api/v1/organizations/1/members/2/suspend")

    assert response.status_code == 200
    assert mock_user_org.is_suspended == True
