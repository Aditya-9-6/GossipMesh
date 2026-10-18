import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.api import app
from gossipmesh.api.deps import get_db
from gossipmesh.db.base import Base
from gossipmesh.models.user import User
from gossipmesh.api.deps import get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    return User(id=1, email="test@example.com", is_active=True)

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_approval_gate_lifecycle():
    response = client.post(
        "/api/v1/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1
        },
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["action_type"] == "push_commit"
    assert data["status"] == "pending"
    approval_id = data["id"]

    # Get approval gate
    get_resp = client.get(f"/api/v1/approvals/{approval_id}", headers={"Authorization": "Bearer test-token"})
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == approval_id

    # Decide approval gate
    decide_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"},
        headers={"Authorization": "Bearer test-token"}
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "approved"
