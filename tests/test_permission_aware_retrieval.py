"""Unit and Cross-Tenant Negative Tests for Permission-Aware Retrieval (Task 78)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.repository import Repository, RepositoryPolicy
from gossipmesh.models.user import User
from gossipmesh.repository.retrieval import PermissionAwareRetriever
from gossipmesh.repository.vector_store import PGVectorStore


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_authorized_retrieval_success(db_session):
    """Verify authorized member can retrieve repository chunks."""
    # 1. Setup Org 1, User 1, Repo 1
    org1 = Organization(id=1, name="Org Alpha")
    user1 = User(id=1, email="alice@alpha.com", hashed_password="pwd", is_superuser=False)
    repo1 = Repository(id=10, organization_id=1, github_id=1010, name="core", full_name="alpha/core")
    db_session.add_all([org1, user1, repo1])
    db_session.flush()

    membership = UserOrganization(user_id=1, organization_id=1)
    db_session.add(membership)
    db_session.commit()

    # 2. Add chunk to vector store
    store = PGVectorStore(db_session)
    vector = [0.1] * 1536
    store.upsert(
        id="chunk-alpha",
        vector=vector,
        metadata={"organization_id": "1", "repo_id": 10, "branch": "main", "filepath": "main.py"},
        content="def alpha_code(): pass",
    )

    retriever = PermissionAwareRetriever(store)
    results = retriever.search(query="alpha", repo_id=10, user=user1, db=db_session)

    assert len(results) == 1
    assert results[0]["id"] == "chunk-alpha"
    assert results[0]["content"] == "def alpha_code(): pass"


def test_cross_tenant_negative_unauthorized_user_blocked(db_session):
    """
    CRITICAL NEGATIVE TEST:
    Verify user from Org Beta attempting to query Org Alpha's repository is strictly blocked.
    """
    org1 = Organization(id=1, name="Org Alpha")
    org2 = Organization(id=2, name="Org Beta")
    user2 = User(id=2, email="bob@beta.com", hashed_password="pwd", is_superuser=False)
    repo1 = Repository(id=10, organization_id=1, github_id=1010, name="core", full_name="alpha/core")
    db_session.add_all([org1, org2, user2, repo1])
    db_session.flush()

    # User 2 belongs only to Org 2
    db_session.add(UserOrganization(user_id=2, organization_id=2))
    db_session.commit()

    store = PGVectorStore(db_session)
    retriever = PermissionAwareRetriever(store)

    # Bob attempts to search Alpha's repo
    with pytest.raises(AuthorizationError) as exc_info:
        retriever.search(query="secrets", repo_id=10, user=user2, db=db_session)

    assert "Access denied" in str(exc_info.value.message)


def test_cross_tenant_zero_data_leakage(db_session):
    """
    CRITICAL NEGATIVE TEST:
    Verify that even with identical query vectors and identical embeddings,
    chunks belonging to other tenants are NEVER returned.
    """
    org1 = Organization(id=1, name="Org Alpha")
    org2 = Organization(id=2, name="Org Beta")
    user1 = User(id=1, email="alice@alpha.com", hashed_password="pwd", is_superuser=False)
    repo1 = Repository(id=10, organization_id=1, github_id=1010, name="alpha-repo", full_name="alpha/repo")
    repo2 = Repository(id=20, organization_id=2, github_id=2020, name="beta-repo", full_name="beta/repo")

    db_session.add_all([org1, org2, user1, repo1, repo2])
    db_session.add(UserOrganization(user_id=1, organization_id=1))
    db_session.commit()

    store = PGVectorStore(db_session)
    identical_vector = [0.333] * 1536

    # Org Alpha chunk
    store.upsert(
        id="alpha-chunk",
        vector=identical_vector,
        metadata={"organization_id": "1", "repo_id": 10, "filepath": "alpha.py"},
        content="Alpha confidential data",
    )

    # Org Beta chunk
    store.upsert(
        id="beta-chunk",
        vector=identical_vector,
        metadata={"organization_id": "2", "repo_id": 20, "filepath": "beta.py"},
        content="Beta confidential secret keys",
    )

    retriever = PermissionAwareRetriever(store)
    results = retriever.search(query="confidential", repo_id=10, user=user1, db=db_session)

    # Only Alpha chunk should be returned
    assert len(results) == 1
    assert results[0]["id"] == "alpha-chunk"
    assert "Beta confidential" not in [r["content"] for r in results]


def test_branch_policy_permission_enforcement(db_session):
    """Verify requesting an unauthorized branch violates branch policy."""
    org1 = Organization(id=1, name="Org Alpha")
    user1 = User(id=1, email="alice@alpha.com", hashed_password="pwd", is_superuser=False)
    repo1 = Repository(id=10, organization_id=1, github_id=1010, name="core", full_name="alpha/core")
    policy1 = RepositoryPolicy(
        repository_id=10,
        allowed_target_branches=["main"],
    )
    db_session.add_all([org1, user1, repo1, policy1])
    db_session.add(UserOrganization(user_id=1, organization_id=1))
    db_session.commit()

    store = PGVectorStore(db_session)
    retriever = PermissionAwareRetriever(store)

    # Requesting non-permitted branch raises AuthorizationError
    with pytest.raises(AuthorizationError) as exc_info:
        retriever.search(query="test", repo_id=10, user=user1, db=db_session, branch="unauthorized-experimental")

    assert "Branch 'unauthorized-experimental' is not permitted" in str(exc_info.value.message)


def test_superuser_audit_bypass(db_session):
    """Verify platform superuser can search for auditing purposes."""
    org1 = Organization(id=1, name="Org Alpha")
    admin_user = User(id=999, email="admin@platform.com", hashed_password="pwd", is_superuser=True)
    repo1 = Repository(id=10, organization_id=1, github_id=1010, name="core", full_name="alpha/core")

    db_session.add_all([org1, admin_user, repo1])
    db_session.commit()

    store = PGVectorStore(db_session)
    store.upsert(
        id="chunk-1",
        vector=[0.1] * 1536,
        metadata={"organization_id": "1", "repo_id": 10},
        content="code snippet",
    )

    retriever = PermissionAwareRetriever(store)
    results = retriever.search(query="audit", repo_id=10, user=admin_user, db=db_session)
    assert len(results) == 1
