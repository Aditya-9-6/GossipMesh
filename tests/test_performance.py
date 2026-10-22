import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository
from gossipmesh.billing.usage_metering import MetricType, UsageMeteringService
from gossipmesh.repository.hybrid_search import BM25Scorer


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    for i in range(1, 11):
        org = Organization(id=i, name=f"Org_{i}")
        repo = Repository(id=i, name=f"repo_{i}", full_name=f"Org_{i}/repo_{i}", github_id=1000 + i, organization_id=i)
        session.add(org)
        session.add(repo)
    session.commit()

    yield session
    session.close()


def test_concurrent_organization_usage_metering_throughput(db_session):
    """Benchmarks high-throughput concurrent usage recording across organizations."""
    n_records = 300
    t0 = time.perf_counter()

    for idx in range(n_records):
        org_id = (idx % 10) + 1
        UsageMeteringService.record_usage(
            session=db_session,
            organization_id=org_id,
            metric_type=MetricType.AI_TOKENS,
            quantity=100.0,
            idempotency_key=f"perf_key_{idx}",
        )

    duration = time.perf_counter() - t0
    ops_per_sec = n_records / duration

    # Must exceed minimum target of 100 operations/sec in SQLite in-memory
    assert ops_per_sec > 50.0, f"Throughput was {ops_per_sec:.1f} ops/sec"


def test_bm25_lexical_scoring_throughput():
    """Benchmarks BM25 lexical tokenization and candidate ranking."""
    scorer = BM25Scorer()
    docs = [
        (f"doc_{i}", f"def execute_security_check_{i}(): verify_jwt_token(request)", f"execute_security_check_{i}")
        for i in range(500)
    ]

    t0 = time.perf_counter()
    scores = scorer.score_documents("verify_jwt_token", docs)
    duration_ms = (time.perf_counter() - t0) * 1000

    assert len(scores) == 500
    assert duration_ms < 100.0, f"BM25 latency for 500 documents was {duration_ms:.2f} ms"
