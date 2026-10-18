import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.models.base import Base
from gossipmesh.models.user import User

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

def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "approver@gossipmesh.test").first()
    if not user:
        user = User(email="approver@gossipmesh.test", hashed_password="dummy", is_active=True, is_superuser=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_user] = override_get_current_user

client = TestClient(app)

def test_approval_gate_lifecycle():
    response = client.post(
        "/approvals/",
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

    res_get = client.get(f"/approvals/{approval_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    res_decide = client.post(
        f"/approvals/{approval_id}/decision",
        json={"decision": "approved"}
    )
    assert res_decide.status_code == 200
    decide_data = res_decide.json()
    assert decide_data["status"] == "approved"
    assert decide_data["approver_id"] is not None
    assert decide_data["approved_at"] is not None
