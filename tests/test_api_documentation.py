import pytest
from fastapi.testclient import TestClient

def test_api_documentation_routes_exist():
    import tests
    from gossipmesh.api.main import app
    client = TestClient(app)

    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()
    assert response.json()["info"]["title"] == "GossipMesh SaaS"
    assert "version" in response.json()["info"]

    response = client.get("/api/v1/docs")
    assert response.status_code == 200

    response = client.get("/api/v1/redoc")
    assert response.status_code == 200

def test_webhook_api_documentation_routes_exist():
    import tests
    from gossipmesh.api.__init__ import app as webhook_app
    client = TestClient(webhook_app)

    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()
    assert response.json()["info"]["title"] == "GossipMesh Webhook API"
    assert "version" in response.json()["info"]

    response = client.get("/docs")
    assert response.status_code == 200
