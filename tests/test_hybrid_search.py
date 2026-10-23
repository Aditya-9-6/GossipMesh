"""Unit tests for Hybrid Search and Reranking (Task 79)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.repository import Repository
from gossipmesh.models.user import User
from gossipmesh.repository.hybrid_search import HybridSearchEngine, SearchResult
from gossipmesh.repository.vector_store import PGVectorStore


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create base org, user, repo
    org = Organization(id=1, name="Acme Corp")
    user = User(id=1, email="alice@acme.com", hashed_password="pwd", is_superuser=False)
    repo = Repository(id=10, organization_id=1, github_id=1001, name="core-api", full_name="acme/core-api")
    membership = UserOrganization(user_id=1, organization_id=1)

    session.add_all([org, user, repo, membership])
    session.commit()

    yield session
    session.close()


def test_hybrid_search_exact_symbol_boost(db_session):
    """Verify BM25 lexical scorer boosts exact symbol name match."""
    store = PGVectorStore(db_session)
    user = db_session.query(User).filter(User.id == 1).first()

    # Chunk 1: contains general auth text
    store.upsert(
        id="chunk-1",
        vector=[0.1] * 1536,
        metadata={"organization_id": "1", "repo_id": 10, "filepath": "auth/service.py", "symbol_name": "AuthService"},
        content="General authentication middleware service",
    )

    # Chunk 2: exact symbol match for rotate_jwt_key
    store.upsert(
        id="chunk-2",
        vector=[0.1] * 1536,
        metadata={"organization_id": "1", "repo_id": 10, "filepath": "crypto/keys.py", "symbol_name": "rotate_jwt_key"},
        content="def rotate_jwt_key(): pass",
    )

    engine = HybridSearchEngine(store)
    results = engine.search(query="rotate_jwt_key", repo_id=10, user=user, db=db_session, alpha=0.3)

    assert len(results) >= 1
    assert results[0].id == "chunk-2"
    assert results[0].citation.symbol_name == "rotate_jwt_key"
    assert results[0].citation.filepath == "crypto/keys.py"


def test_metadata_filtering(db_session):
    """Verify path pattern include and exclude filtering."""
    store = PGVectorStore(db_session)
    user = db_session.query(User).filter(User.id == 1).first()

    store.upsert(
        id="chunk-app",
        vector=[0.2] * 1536,
        metadata={"organization_id": "1", "repo_id": 10, "filepath": "src/app.py"},
        content="app definition",
    )
    store.upsert(
        id="chunk-test",
        vector=[0.2] * 1536,
        metadata={"organization_id": "1", "repo_id": 10, "filepath": "tests/test_app.py"},
        content="test app",
    )

    engine = HybridSearchEngine(store)

    # Filter to only src/*.py
    results = engine.search(
        query="app",
        repo_id=10,
        user=user,
        db=db_session,
        metadata_filter={"path_pattern": "src/*"},
    )
    assert len(results) == 1
    assert results[0].id == "chunk-app"


def test_duplicate_chunk_removal(db_session):
    """Verify duplicate chunks with identical hash are deduplicated."""
    store = PGVectorStore(db_session)
    user = db_session.query(User).filter(User.id == 1).first()

    # Upsert two chunks with identical hash and content
    common_hash = "abcdef1234567890" * 4
    store.upsert(
        id="chunk-dup-1",
        vector=[0.3] * 1536,
        metadata={"organization_id": "1", "repo_id": 10, "filepath": "a.py", "chunk_hash": common_hash},
        content="identical code chunk",
    )
    store.upsert(
        id="chunk-dup-2",
        vector=[0.3] * 1536,
        metadata={"organization_id": "1", "repo_id": 10, "filepath": "a.py", "chunk_hash": common_hash},
        content="identical code chunk",
    )

    engine = HybridSearchEngine(store)
    results = engine.search(query="code chunk", repo_id=10, user=user, db=db_session)

    assert len(results) == 1


def test_context_budget_limit(db_session):
    """Verify context character budget limits returned content size."""
    store = PGVectorStore(db_session)
    user = db_session.query(User).filter(User.id == 1).first()

    large_content_1 = "A" * 500
    large_content_2 = "B" * 500

    store.upsert("chunk-large-1", vector=[0.1] * 1536, metadata={"organization_id": "1", "repo_id": 10, "filepath": "a.py"}, content=large_content_1)
    store.upsert("chunk-large-2", vector=[0.1] * 1536, metadata={"organization_id": "1", "repo_id": 10, "filepath": "b.py"}, content=large_content_2)

    engine = HybridSearchEngine(store)

    # Limit context to 600 characters: only 1 chunk should fit
    results = engine.search(
        query="AB",
        repo_id=10,
        user=user,
        db=db_session,
        max_context_chars=600,
        top_k=5,
    )

    assert len(results) == 1
    assert len(results[0].content) == 500


def test_deterministic_ordering_tie_breaking(db_session):
    """Verify tie-breaking is strictly deterministic when scores are identical."""
    store = PGVectorStore(db_session)
    user = db_session.query(User).filter(User.id == 1).first()

    store.upsert("chunk-z", vector=[0.5] * 1536, metadata={"organization_id": "1", "repo_id": 10, "filepath": "z_file.py", "chunk_index": 0}, content="equal match")
    store.upsert("chunk-a", vector=[0.5] * 1536, metadata={"organization_id": "1", "repo_id": 10, "filepath": "a_file.py", "chunk_index": 0}, content="equal match")

    engine = HybridSearchEngine(store)
    results = engine.search(query="equal match", repo_id=10, user=user, db=db_session)

    assert len(results) == 2
    # Deterministic tie-breaking orders by filepath ASC
    assert results[0].filepath == "a_file.py"
    assert results[1].filepath == "z_file.py"
