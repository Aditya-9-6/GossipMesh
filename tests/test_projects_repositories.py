"""Unit and integration tests for Project and Repository APIs (Task 37)."""

import os

os.environ["TESTING"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.organization import Organization, UserOrganization, OrganizationRole
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository, RepositoryPolicy


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def test_db(engine):
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine):
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[deps.get_db] = override_get_db
    test_client = TestClient(app, raise_server_exceptions=True)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


def test_project_lifecycle(client, test_db):
    # Setup Org, User (Admin)
    org = Organization(id=1, name="Acme Org")
    admin_user = User(id=1, email="admin@acme.com", is_superuser=False)
    test_db.add_all([org, admin_user])
    test_db.flush()

    user_org = UserOrganization(user_id=1, organization_id=1, role=OrganizationRole.organization_admin)
    test_db.add(user_org)
    test_db.commit()

    app.dependency_overrides[deps.get_current_user] = lambda: admin_user

    # 1. Create Project
    res = client.post(
        "/api/v1/organizations/1/projects", json={"name": "Core Backend", "description": "Backend services"}
    )
    assert res.status_code == 200, res.text
    project_data = res.json()
    proj_id = project_data["id"]
    assert project_data["name"] == "Core Backend"

    # 2. List Projects
    res = client.get("/api/v1/organizations/1/projects")
    assert res.status_code == 200
    projects_list = res.json()
    assert len(projects_list) == 1
    assert projects_list[0]["id"] == proj_id

    # 3. Get Project details
    res = client.get(f"/api/v1/projects/{proj_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Core Backend"
    assert res.json()["repositories"] == []

    # 4. Update Project
    res = client.patch(f"/api/v1/projects/{proj_id}", json={"name": "Core Backend V2", "description": "Updated desc"})
    assert res.status_code == 200
    assert res.json()["name"] == "Core Backend V2"
    assert res.json()["description"] == "Updated desc"

    # 5. Delete Project
    res = client.delete(f"/api/v1/projects/{proj_id}")
    assert res.status_code == 200

    # 6. Verify Deleted
    res = client.get(f"/api/v1/projects/{proj_id}")
    assert res.status_code == 404


def test_repository_connection_branch_selection_and_policy(client, test_db):
    org = Organization(id=2, name="Beta Org")
    admin = User(id=10, email="lead@beta.com", is_superuser=False)
    test_db.add_all([org, admin])
    test_db.flush()

    user_org = UserOrganization(user_id=10, organization_id=2, role=OrganizationRole.owner)
    test_db.add(user_org)
    test_db.commit()

    app.dependency_overrides[deps.get_current_user] = lambda: admin

    # 1. Connect Repository
    res = client.post(
        "/api/v1/organizations/2/repositories",
        json={
            "github_id": 98765,
            "name": "gossip-mesh-node",
            "full_name": "beta-org/gossip-mesh-node",
            "default_branch": "main",
        },
    )
    assert res.status_code == 200, res.text
    repo_data = res.json()
    repo_id = repo_data["id"]
    assert repo_data["name"] == "gossip-mesh-node"

    # 2. List Repositories
    res = client.get("/api/v1/organizations/2/repositories")
    assert res.status_code == 200
    repos = res.json()
    assert len(repos) == 1
    assert repos[0]["id"] == repo_id

    # 3. Get Repository Details & Default Policy
    res = client.get(f"/api/v1/repositories/{repo_id}")
    assert res.status_code == 200
    details = res.json()
    assert details["default_branch"] == "main"
    assert details["policy"] is not None
    assert details["policy"]["branch_protection_enabled"] is True
    assert details["policy"]["min_approvals"] == 1

    # 4. Branch Selection
    res = client.patch(f"/api/v1/repositories/{repo_id}/branch", json={"default_branch": "develop"})
    assert res.status_code == 200
    assert res.json()["default_branch"] == "develop"

    # 5. Policy Configuration Update
    res = client.patch(
        f"/api/v1/repositories/{repo_id}/policy",
        json={
            "auto_merge_enabled": True,
            "min_approvals": 2,
            "allowed_target_branches": ["develop", "main"],
            "max_diff_lines": 1000,
            "custom_rules": {"enforce_conventional_commits": True},
        },
    )
    assert res.status_code == 200
    policy_data = res.json()
    assert policy_data["auto_merge_enabled"] is True
    assert policy_data["min_approvals"] == 2
    assert policy_data["allowed_target_branches"] == ["develop", "main"]
    assert policy_data["custom_rules"]["enforce_conventional_commits"] is True

    # 6. Repository Removal
    res = client.delete(f"/api/v1/repositories/{repo_id}")
    assert res.status_code == 200

    # Verify 404 after removal
    res = client.get(f"/api/v1/repositories/{repo_id}")
    assert res.status_code == 404


def test_project_repository_link_and_unlink(client, test_db):
    org = Organization(id=3, name="Gamma Org")
    user = User(id=20, email="dev@gamma.com", is_superuser=False)
    test_db.add_all([org, user])
    test_db.flush()

    user_org = UserOrganization(user_id=20, organization_id=3, role=OrganizationRole.organization_admin)
    test_db.add(user_org)

    proj = Project(id=50, organization_id=3, name="Gamma Core")
    repo = Repository(
        id=60, organization_id=3, github_id=4455, name="gamma-repo", full_name="gamma/repo", default_branch="main"
    )
    test_db.add_all([proj, repo])
    test_db.commit()

    app.dependency_overrides[deps.get_current_user] = lambda: user

    # 1. Link Repo to Project
    res = client.post(f"/api/v1/projects/50/repositories/60")
    assert res.status_code == 200
    proj_data = res.json()
    assert len(proj_data["repositories"]) == 1
    assert proj_data["repositories"][0]["id"] == 60

    # 2. Unlink Repo from Project
    res = client.delete(f"/api/v1/projects/50/repositories/60")
    assert res.status_code == 200
    proj_data = res.json()
    assert len(proj_data["repositories"]) == 0


def test_permission_enforcement(client, test_db):
    org = Organization(id=4, name="Delta Org")
    dev_user = User(id=30, email="developer@delta.com", is_superuser=False)
    test_db.add_all([org, dev_user])
    test_db.flush()

    user_org = UserOrganization(user_id=30, organization_id=4, role=OrganizationRole.developer)
    test_db.add(user_org)

    repo = Repository(
        id=70, organization_id=4, github_id=9999, name="delta-repo", full_name="delta/repo", default_branch="main"
    )
    test_db.add(repo)
    test_db.commit()

    app.dependency_overrides[deps.get_current_user] = lambda: dev_user

    # Developer CAN select branch
    res = client.patch(f"/api/v1/repositories/70/branch", json={"default_branch": "feature/branch"})
    assert res.status_code == 200

    # Developer CANNOT update repository policy (admin required)
    res = client.patch(f"/api/v1/repositories/70/policy", json={"auto_merge_enabled": True})
    assert res.status_code == 403

    # Developer CANNOT delete repository (admin required)
    res = client.delete(f"/api/v1/repositories/70")
    assert res.status_code == 403
