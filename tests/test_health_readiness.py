import os
os.environ["TESTING"] = "true"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.api.main import app
from gossipmesh.api.deps import get_db
from gossipmesh.models.base import Base


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_liveness_probe(client):
    res = client.get("/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}


def test_readiness_probe(client):
    res = client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "database" in data["components"]
    assert "redis" in data["components"]
    assert "migrations" in data["components"]
    assert "workers" in data["components"]
    assert "providers" in data["components"]
    assert data["components"]["database"]["status"] == "healthy"


def test_individual_subsystem_health_probes(client):
    # Database probe
    db_res = client.get("/health/database")
    assert db_res.status_code == 200
    assert db_res.json()["status"] == "healthy"

    # Redis probe
    redis_res = client.get("/health/redis")
    assert redis_res.status_code == 200
    assert redis_res.json()["status"] == "healthy"

    # Migrations probe
    mig_res = client.get("/health/migrations")
    assert mig_res.status_code == 200
    assert mig_res.json()["status"] == "healthy"

    # Workers probe
    worker_res = client.get("/health/workers")
    assert worker_res.status_code == 200
    assert worker_res.json()["status"] == "healthy"

    # Providers probe
    prov_res = client.get("/health/providers")
    assert prov_res.status_code == 200
    assert prov_res.json()["status"] == "healthy"


def test_zero_secrets_exposure_in_health_endpoints(client):
    endpoints = [
        "/health/live",
        "/health/ready",
        "/health/database",
        "/health/redis",
        "/health/migrations",
        "/health/workers",
        "/health/providers",
    ]
    for ep in endpoints:
        res = client.get(ep)
        body = res.text.lower()
        # Ensure zero credentials or secret keys are exposed
        assert "password" not in body
        assert "secret" not in body or "secret_key" not in body
        assert "sk-" not in body
        assert "ghp_" not in body
        assert "postgres://" not in body
