import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api import app
from gossipmesh.models.base import Base
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.core.config import settings
from gossipmesh.models.approval import ApprovalGate
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
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

<<<<<<< HEAD
async def override_get_current_user():
    return User(
        id="test-user-id",
        email="test@gossipmesh.internal",
        name="testuser",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False
    )

app.dependency_overrides[deps.get_db] = override_get_db
app.dependency_overrides[deps.get_current_user] = override_get_current_user
=======

def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "approver@gossipmesh.test").first()
    if not user:
        user = User(
            email="approver@gossipmesh.test",
            hashed_password="dummy",
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user


@pytest.fixture(autouse=True)
def setup_overrides():
    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(deps.get_db, None)
    app.dependency_overrides.pop(deps.get_current_user, None)


>>>>>>> origin/main
client = TestClient(app)


def test_approval_gate_lifecycle():
    headers = {"Authorization": "Bearer test-token"}
    response = client.post(
        f"{settings.API_V1_STR}/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
<<<<<<< HEAD
            "expires_in_hours": 1
        },
        headers=headers
=======
            "expires_in_hours": 1,
        },
>>>>>>> origin/main
    )
    assert response.status_code == 201
    data = response.json()
    approval_id = data["id"]
    assert data["status"] == "pending"
    assert data["commit_sha"] == "abc1234"

<<<<<<< HEAD
    res_get = client.get(f"/api/v1/approvals/{approval_id}", headers=headers)
=======
    res_get = client.get(f"{settings.API_V1_STR}/approvals/{approval_id}")
>>>>>>> origin/main
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    res_decide = client.post(
<<<<<<< HEAD
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"},
        headers=headers
=======
        f"{settings.API_V1_STR}/approvals/{approval_id}/decision",
        json={"decision": "approved"},
>>>>>>> origin/main
    )
    assert res_decide.status_code == 200
    decide_data = res_decide.json()
    assert decide_data["status"] == "approved"
    assert decide_data["approver_id"] is not None
    assert decide_data["approved_at"] is not None
