"""Unit tests for Tenant-scoped queries, context isolation, and cross-organization guards (Task 35)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.db.tenant import TenantContext, TenantQueryGuard
from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.repository import Repository
from gossipmesh.models.runtime import Workflow, Job
from gossipmesh.models.user import User


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_tenant_context_manager():
    assert TenantQueryGuard.get_current_tenant_id() is None

    with TenantContext(101):
        assert TenantQueryGuard.get_current_tenant_id() == 101
        with TenantContext(202):
            assert TenantQueryGuard.get_current_tenant_id() == 202
        assert TenantQueryGuard.get_current_tenant_id() == 101

    assert TenantQueryGuard.get_current_tenant_id() is None


def test_assert_tenant_access():
    # 1. Superuser allows any org
    superuser = User(id=1, email="root@gossipmesh.io", is_superuser=True)
    TenantQueryGuard.assert_tenant_access(superuser, organization_id=999)

    # 2. Regular user linked via UserOrganization
    user = User(id=2, email="user@tenant10.com", is_superuser=False)
    user_org = UserOrganization(user_id=2, organization_id=10)
    user.organizations = [user_org]
    TenantQueryGuard.assert_tenant_access(user, organization_id=10)

    # 3. User with direct organization_id attribute
    user2 = User(id=3, email="user@tenant20.com", is_superuser=False)
    user2.organization_id = 20
    TenantQueryGuard.assert_tenant_access(user2, organization_id=20)

    # 4. Unauthorized org access raises AuthorizationError
    with pytest.raises(AuthorizationError) as exc:
        TenantQueryGuard.assert_tenant_access(user, organization_id=99)
    assert "Access denied" in str(exc.value.message)


def test_filter_query_tenant_isolation(db_session):
    # Setup data for two tenants
    org1 = Organization(id=1, name="Tenant One")
    org2 = Organization(id=2, name="Tenant Two")
    db_session.add_all([org1, org2])

    repo1 = Repository(id=10, organization_id=1, github_id=1001, full_name="org1/repo-one", name="repo-one", default_branch="main")
    repo2 = Repository(id=20, organization_id=2, github_id=2002, full_name="org2/repo-two", name="repo-two", default_branch="main")
    db_session.add_all([repo1, repo2])

    wf1 = Workflow(id=100, organization_id=1, repository_id=10, status="running")
    wf2 = Workflow(id=200, organization_id=2, repository_id=20, status="running")
    db_session.add_all([wf1, wf2])

    job1 = Job(id=1000, workflow_id=100, agent_name="reviewer", status="completed")
    job2 = Job(id=2000, workflow_id=200, agent_name="reviewer", status="completed")
    db_session.add_all([job1, job2])
    db_session.commit()

    # Query without active tenant raises AuthorizationError
    with pytest.raises(AuthorizationError) as exc:
        TenantQueryGuard.filter_query(db_session, Repository).all()
    assert "Tenant isolation violation" in str(exc.value.message)

    # Query with explicit organization_id parameter
    repos_org1 = TenantQueryGuard.filter_query(db_session, Repository, organization_id=1).all()
    assert len(repos_org1) == 1
    assert repos_org1[0].name == "repo-one"

    # Query within TenantContext for Org 1
    with TenantContext(1):
        # Organization model itself
        orgs = TenantQueryGuard.filter_query(db_session, Organization).all()
        assert len(orgs) == 1
        assert orgs[0].name == "Tenant One"

        # Direct organization_id column (Repository)
        repos = TenantQueryGuard.filter_query(db_session, Repository).all()
        assert len(repos) == 1
        assert repos[0].id == 10

        # Workflow
        workflows = TenantQueryGuard.filter_query(db_session, Workflow).all()
        assert len(workflows) == 1
        assert workflows[0].id == 100

        # Linked model via workflow_id (Job)
        jobs = TenantQueryGuard.filter_query(db_session, Job).all()
        assert len(jobs) == 1
        assert jobs[0].id == 1000

    # Query within TenantContext for Org 2
    with TenantContext(2):
        repos = TenantQueryGuard.filter_query(db_session, Repository).all()
        assert len(repos) == 1
        assert repos[0].id == 20

        jobs = TenantQueryGuard.filter_query(db_session, Job).all()
        assert len(jobs) == 1
        assert jobs[0].id == 2000


def test_filter_query_unsupported_model(db_session):
    class DummyUnscopedModel:
        pass

    with pytest.raises(ValueError) as exc:
        TenantQueryGuard.filter_query(db_session, DummyUnscopedModel, organization_id=1)
    assert "has no defined organization scoping path" in str(exc.value)


def test_scope_utilities():
    # Cache key scoping
    cache_key = TenantQueryGuard.scope_cache_key("repo:commits:main", organization_id=42)
    assert cache_key == "tenant:42:cache:repo:commits:main"

    # Vector filter scoping
    vec_filter = TenantQueryGuard.scope_vector_filter(
        organization_id=42, base_filter={"file_type": "python"}
    )
    assert vec_filter == {"file_type": "python", "organization_id": 42}

    # Artifact path scoping with directory traversal sanitization
    art_path = TenantQueryGuard.scope_artifact_path(
        organization_id=42, filename="../../etc/passwd.patch"
    )
    assert art_path == "artifacts/42/etc/passwd.patch"
    assert ".." not in art_path
