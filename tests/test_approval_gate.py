import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api.main import app, get_db, get_current_user
from gossipmesh.api import deps
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.core.config import settings
from gossipmesh.models.approval import ApprovalGateModel, ApprovalGate
import gossipmesh.models

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "admin_test").first()
    if not user:
        user = User(
            username="admin_test",
            email="approver@gossipmesh.test",
            hashed_password="dummy",
            role="admin",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_user] = override_get_current_user


@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(deps.get_db, None)
    app.dependency_overrides.pop(deps.get_current_user, None)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


def test_approval_gate_lifecycle():
    db = TestingSessionLocal()
    # Ensure test user exists
    user = db.query(User).filter(User.username == "admin_test").first()
    if not user:
        user = User(
            username="admin_test",
            email="approver@gossipmesh.test",
            hashed_password="dummy",
            role="admin",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
    db.close()

    # Test initial status or submission from feature branch
    payload_data = {"action": "deploy_cluster", "target": "us-west-2"}
    response = client.post("/api/v1/approval/submit", json=payload_data)
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data or "status" in data

    # Test full approval endpoint lifecycle from origin/main
    response_main = client.post(
        f"{settings.API_V1_STR}/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1,
        },
    )
    assert response_main.status_code == 201
    data_main = response_main.json()
    approval_id = data_main["id"]
    assert data_main["status"] == "pending"
    assert data_main["commit_sha"] == "abc1234"

    res_get = client.get(f"{settings.API_V1_STR}/approvals/{approval_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    res_decide = client.post(
        f"{settings.API_V1_STR}/approvals/{approval_id}/decision",
        json={"decision": "approved"},
    )
    assert res_decide.status_code == 200
    decide_data = res_decide.json()
    assert decide_data["status"] == "approved"
    assert decide_data["approver_id"] is not None
    assert decide_data["approved_at"] is not None
