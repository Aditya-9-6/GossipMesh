"""Unit tests for Production Vector Storage (Task 75)."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.repository.vector_store import DocumentChunk, PGVectorStore


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_upsert_stores_full_production_metadata(db_session):
    """Verify storing organization, repository, branch, file, chunk, hash, provider, and version."""
    store = PGVectorStore(db_session)

    metadata = {
        "organization_id": "org-corp-1",
        "repository_id": 42,
        "branch": "feature/ai-review",
        "filepath": "gossipmesh/crypto/vault.py",
        "chunk_index": 0,
        "provider": "openai:text-embedding-3-small",
        "embedding_version": "v2",
        "extra_info": "auth token handler",
    }
    content = "def authenticate_token(token: str): pass"
    vector = [0.1] * 1536

    chunk = store.upsert(
        id="chunk-corp-1",
        vector=vector,
        metadata=metadata,
        content=content,
    )

    assert chunk.id == "chunk-corp-1"
    assert chunk.organization_id == "org-corp-1"
    assert chunk.repository_id == 42
    assert chunk.branch == "feature/ai-review"
    assert chunk.filepath == "gossipmesh/crypto/vault.py"
    assert chunk.chunk_index == 0
    assert chunk.chunk_hash is not None
    assert len(chunk.chunk_hash) == 64  # SHA-256
    assert chunk.provider == "openai:text-embedding-3-small"
    assert chunk.embedding_version == "v2"
    assert chunk.is_deleted is False


def test_tenant_isolation_in_vector_search(db_session):
    """Verify that vector searches strictly isolate results between tenant organizations."""
    store = PGVectorStore(db_session)
    vector = [0.2] * 1536

    # Org A chunk
    store.upsert(
        id="chunk-org-a",
        vector=vector,
        metadata={"organization_id": "org_A", "repo_id": 1, "filepath": "a.py"},
        content="Secret Org A algorithm",
    )

    # Org B chunk
    store.upsert(
        id="chunk-org-b",
        vector=vector,
        metadata={"organization_id": "org_B", "repo_id": 2, "filepath": "b.py"},
        content="Secret Org B algorithm",
    )

    # Search scoped to Org A
    results_a = store.search(vector, filter={"organization_id": "org_A", "repo_id": 1}, top_k=5)
    assert len(results_a) == 1
    assert results_a[0]["id"] == "chunk-org-a"
    assert results_a[0]["organization_id"] == "org_A"

    # Search scoped to Org B
    results_b = store.search(vector, filter={"organization_id": "org_B", "repo_id": 2}, top_k=5)
    assert len(results_b) == 1
    assert results_b[0]["id"] == "chunk-org-b"
    assert results_b[0]["organization_id"] == "org_B"


def test_soft_deletion_and_retention_filtering(db_session):
    """Verify soft-deleted and expired chunks are excluded from search."""
    store = PGVectorStore(db_session)
    vector = [0.5] * 1536

    # 1. Normal active chunk
    store.upsert(
        id="active-chunk",
        vector=vector,
        metadata={"organization_id": "org_1", "repo_id": 10},
        content="Active code",
    )

    # 2. Soft-deleted chunk
    store.upsert(
        id="deleted-chunk",
        vector=vector,
        metadata={"organization_id": "org_1", "repo_id": 10},
        content="Old deleted code",
    )
    store.soft_delete("deleted-chunk")

    # 3. Retention expired chunk
    past_time = datetime.now(timezone.utc) - timedelta(days=2)
    store.upsert(
        id="expired-chunk",
        vector=vector,
        metadata={"organization_id": "org_1", "repo_id": 10, "retention_expires_at": past_time},
        content="Expired code",
    )

    results = store.search(vector, filter={"organization_id": "org_1", "repo_id": 10}, top_k=10)
    result_ids = [r["id"] for r in results]

    assert "active-chunk" in result_ids
    assert "deleted-chunk" not in result_ids
    assert "expired-chunk" not in result_ids

    # Purge expired chunks
    purged_count = store.purge_expired("org_1")
    assert purged_count == 1


def test_similarity_ranking_order(db_session):
    """Verify closest vector has higher score and comes first."""
    store = PGVectorStore(db_session)

    # Chunk 1: very close to [1.0, 1.0, ...]
    v1 = [1.0] * 1536
    store.upsert("chunk-close", vector=v1, metadata={"organization_id": "org_1", "repo_id": 1}, content="Close match")

    # Chunk 2: far away from [1.0, 1.0, ...]
    v2 = [10.0] * 1536
    store.upsert("chunk-far", vector=v2, metadata={"organization_id": "org_1", "repo_id": 1}, content="Far match")

    query_v = [1.01] * 1536
    results = store.search(query_v, filter={"organization_id": "org_1", "repo_id": 1}, top_k=2)

    assert len(results) == 2
    assert results[0]["id"] == "chunk-close"
    assert results[0]["score"] > results[1]["score"]
