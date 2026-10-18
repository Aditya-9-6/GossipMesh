import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api import app
from gossipmesh.api import deps
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.approval import ApprovalGate

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "test_approver").first()
    if not user:
        user = User(username="test_approver", email="approver@gossipmesh.test", hashed_password="fakepass", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_user] = override_get_current_user

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

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
    assert response.status_code == 201, response.text
    data = response.json()
    approval_id = data["id"]
    assert data["status"] == "pending"
    assert data["action_type"] == "push_commit"

    # Get approval gate
    get_resp = client.get(f"/api/v1/approvals/{approval_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "pending"

    # Decide approval
    decide_resp = client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"}
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "approved"
