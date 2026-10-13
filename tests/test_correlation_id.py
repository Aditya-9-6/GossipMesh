import tests
import pytest
from fastapi.testclient import TestClient
from gossipmesh.api.main import app
import uuid
from fastapi import APIRouter
from gossipmesh.api.background_tasks import CorrelationIdBackgroundTasks

client = TestClient(app)

router = APIRouter()

@router.post("/test-background-task")
async def bg_task_endpoint(background_tasks: CorrelationIdBackgroundTasks):
    from gossipmesh.middleware.correlation import get_correlation_id

    req_id = get_correlation_id()

    def background_job(expected_id):
        pass

    background_tasks.add_task(background_job, req_id)
    return {"status": "ok"}

app.include_router(router)


def test_correlation_id_middleware_generates_id():
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    val = response.headers["X-Correlation-ID"]
    assert uuid.UUID(val, version=4)

def test_correlation_id_middleware_accepts_valid_id():
    test_id = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Correlation-ID": test_id})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == test_id

def test_correlation_id_middleware_rejects_invalid_id_and_generates_new():
    invalid_id = "not-a-uuid"
    response = client.get("/health", headers={"X-Correlation-ID": invalid_id})
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Correlation-ID"] != invalid_id
    val = response.headers["X-Correlation-ID"]
    assert uuid.UUID(val, version=4)

def test_correlation_id_in_error_response():
    response = client.get("/invalid-route-that-does-not-exist")
    assert response.status_code == 404
    assert "X-Correlation-ID" in response.headers
    data = response.json()
    assert "correlation_id" in data
    assert data["correlation_id"] == response.headers["X-Correlation-ID"]

def test_correlation_id_in_background_tasks():
    response = client.post("/test-background-task")
    assert response.status_code == 200
