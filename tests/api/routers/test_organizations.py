import pytest
from unittest.mock import MagicMock
from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, UserOrganization, OrganizationInvitation
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository

@pytest.fixture
def mock_current_user():
    user = User(id=1, email="test@example.com", hashed_password="hashed")
    app.dependency_overrides[deps.get_current_user] = lambda: user
    yield user



@pytest.fixture
def mock_db_session():
    return MagicMock()

def test_create_organization(test_client, mock_db_session, mock_current_user):
def test_create_organization(test_client, mock_current_user):
    mock_db_session = MagicMock()
    # Mock db queries
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    def side_effect(obj):
        if getattr(obj, '__tablename__', None) == 'organizations' or isinstance(obj, Organization):
            obj.id = 1
        if getattr(obj, '__tablename__', None) == 'user_organizations' or isinstance(obj, UserOrganization):
            pass
    mock_db_session.add.side_effect = side_effect

    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post("/api/v1/organizations/", json={"name": "New Org"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "New Org"}

def test_create_organization_exists(test_client, mock_db_session, mock_current_user):
def test_create_organization_exists(test_client, mock_current_user):
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = Organization(id=1, name="Existing")
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post("/api/v1/organizations/", json={"name": "Existing"})
    assert response.status_code == 400

def test_create_invitation(test_client, mock_db_session, mock_current_user):
def test_create_invitation(test_client, mock_current_user):
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = UserOrganization(role="admin", is_suspended=False)
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post("/api/v1/organizations/1/invitations", json={"email": "invite@example.com", "role": "member"})

    assert response.status_code == 200
    assert "token" in response.json()

def test_create_invitation_unauthorized(test_client, mock_db_session, mock_current_user):
def test_create_invitation_unauthorized(test_client, mock_current_user):
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None # Not an admin
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post("/api/v1/organizations/1/invitations", json={"email": "invite@example.com", "role": "member"})

    assert response.status_code == 403

def test_accept_invitation(test_client, mock_db_session, mock_current_user):
def test_accept_invitation(test_client, mock_current_user):
    mock_db_session = MagicMock()
    # Mock finding the invitation
    mock_invitation = OrganizationInvitation(id=1, email="invite@example.com", token="valid_token", organization_id=1, role="member")

    # First query is for invitation, second is for existing member
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_invitation, None]
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post("/api/v1/organizations/invitations/valid_token/accept")

    assert response.status_code == 200
    assert mock_db_session.add.call_count == 2 # UserOrg, AuditEvent
    assert mock_db_session.delete.call_count == 1 # Invitation

def test_assign_role(test_client, mock_db_session, mock_current_user):
def test_assign_role(test_client, mock_current_user):
    mock_db_session = MagicMock()
    # First query checks admin, second finds the user to update
    mock_admin_check = UserOrganization(role="admin", is_suspended=False)
    mock_user_org = UserOrganization(organization_id=1, user_id=2, role="member")
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_admin_check, mock_user_org]
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.patch("/api/v1/organizations/1/members/2/role", json={"role": "admin"})

    assert response.status_code == 200
    assert mock_user_org.role == "admin"

def test_create_project(test_client, mock_db_session, mock_current_user):
def test_create_project(test_client, mock_current_user):
    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = UserOrganization(role="admin", is_suspended=False)

    def side_effect(obj):
        if isinstance(obj, Project):
            obj.id = 1
    mock_db_session.add.side_effect = side_effect
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post("/api/v1/organizations/1/projects", json={"name": "New Project", "description": "Desc"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "New Project", "description": "Desc"}

def test_connect_repository(test_client, mock_db_session, mock_current_user):
def test_connect_repository(test_client, mock_current_user):
    mock_db_session = MagicMock()
    # First query admin check, second repo check
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [UserOrganization(role="admin", is_suspended=False), None]

    def side_effect(obj):
        if getattr(obj, "__tablename__", "") == "repositories" or isinstance(obj, Repository):
            obj.id = 1
            try:
                obj.is_active = True
                obj.is_archived = False
                obj.installation_id = None
            except AttributeError:
                pass
    mock_db_session.add.side_effect = side_effect
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.post("/api/v1/organizations/1/repositories", json={"github_id": 123, "name": "repo", "full_name": "org/repo", "default_branch": "main"})

    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_remove_member(test_client, mock_db_session, mock_current_user):
def test_remove_member(test_client, mock_current_user):
    mock_db_session = MagicMock()
    # First admin check, second find member
    mock_admin_check = UserOrganization(role="admin", is_suspended=False)
    mock_user_org = UserOrganization(organization_id=1, user_id=2, role="member")
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_admin_check, mock_user_org]
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.delete("/api/v1/organizations/1/members/2")

    assert response.status_code == 200
    assert mock_db_session.delete.call_count == 1

def test_suspend_member(test_client, mock_db_session, mock_current_user):
def test_suspend_member(test_client, mock_current_user):
    mock_db_session = MagicMock()
    # First admin check, second find member
    mock_admin_check = UserOrganization(role="admin", is_suspended=False)
    mock_user_org = UserOrganization(organization_id=1, user_id=2, role="member", is_suspended=False)
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [mock_admin_check, mock_user_org]
    app.dependency_overrides[deps.get_db] = lambda: mock_db_session

    response = test_client.patch("/api/v1/organizations/1/members/2/suspend")

    assert response.status_code == 200
    assert mock_user_org.is_suspended == True
