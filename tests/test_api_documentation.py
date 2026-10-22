import os
import pytest
from fastapi.testclient import TestClient

# Set TESTING to avoid database connectivity attempts during startup
os.environ["TESTING"] = "true"


def test_api_documentation_routes_exist():
    from gossipmesh.api.main import app

    client = TestClient(app)

    # 1. Verify OpenAPI JSON endpoint
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "openapi" in spec
    assert spec["info"]["title"] == "GossipMesh SaaS"
    assert "version" in spec["info"]
    assert spec["info"]["version"] == "0.2.0"

    # Verify structured OpenAPI tags
    tag_names = {t["name"] for t in spec.get("tags", [])}
    assert "auth" in tag_names
    assert "organizations" in tag_names
    assert "repositories" in tag_names
    assert "billing" in tag_names
    assert "health" in tag_names

    # 2. Verify Swagger UI route
    docs_response = client.get("/api/v1/docs")
    assert docs_response.status_code == 200
    assert "swagger-ui" in docs_response.text.lower() or "html" in docs_response.headers.get("content-type", "")

    # 3. Verify ReDoc route
    redoc_response = client.get("/api/v1/redoc")
    assert redoc_response.status_code == 200
    assert "redoc" in redoc_response.text.lower() or "html" in redoc_response.headers.get("content-type", "")


def test_webhook_api_documentation_routes_exist():
    from gossipmesh.api import app as webhook_app

    client = TestClient(webhook_app)

    # 1. Verify OpenAPI JSON endpoint
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "openapi" in spec
    assert spec["info"]["title"] == "GossipMesh Webhook API"
    assert spec["info"]["version"] == "0.2.0"

    # 2. Verify Swagger UI route
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200


def test_openapi_schema_contains_core_paths():
    from gossipmesh.api.main import app

    client = TestClient(app)
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})

    # Ensure core enterprise routes are present in OpenAPI catalog
    assert "/api/v1/auth/login" in paths or any("auth" in p for p in paths)
    assert any("billing" in p for p in paths)
    assert any("repositories" in p for p in paths)
