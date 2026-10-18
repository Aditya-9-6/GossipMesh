import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.api import app
from gossipmesh.api.deps import get_db, get_current_user
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.approval import ApprovalGate

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_auth_override():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(id=1, email="test@example.com", hashed_password="dummy", is_active=True, is_superuser=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()

    app.dependency_overrides[get_current_user] = lambda: User(id=1, email="test@example.com", is_active=True, is_superuser=True)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)

def test_approval_gate_lifecycle():
    response = client.post(
        "/api/v1/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1
        }
    )
    assert response.status_code == 201
    data = response.json()
    approval_id = data["id"]
    assert data["status"] == "pending"
    assert data["commit_sha"] == "abc1234"

    res_get = client.get(f"/api/v1/approvals/{approval_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    res_decide = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"}
    )
    assert res_decide.status_code == 200
    decide_data = res_decide.json()
    assert decide_data["status"] == "approved"
