import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api import app
from gossipmesh.api.deps import get_db
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
<<<<<<< HEAD
from gossipmesh.models.approval import ApprovalGate
=======
from gossipmesh.core.config import settings
from gossipmesh.models.approval import ApprovalGate
import gossipmesh.models
>>>>>>> origin/main

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

<<<<<<< HEAD
app.dependency_overrides[get_db] = override_get_db

# Mock current user dependency if needed
from gossipmesh.api.deps import get_current_user
=======

>>>>>>> origin/main
def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
<<<<<<< HEAD
        user = User(email="test@example.com", hashed_password="fakepass")
=======
        user = User(
            email="approver@gossipmesh.test",
            hashed_password="dummy",
            is_active=True,
            is_superuser=True,
        )
>>>>>>> origin/main
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

<<<<<<< HEAD
app.dependency_overrides[get_current_user] = override_get_current_user
=======

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
    response = client.post(
        f"{settings.API_V1_STR}/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
<<<<<<< HEAD
            "expires_in_hours": 1
        },
        headers={"Authorization": "Bearer test-token"}
=======
            "expires_in_hours": 1,
        },
>>>>>>> origin/main
    )
    assert response.status_code == 201
    data = response.json()
    assert data["action_type"] == "push_commit"
    assert data["status"] == "pending"
    approval_id = data["id"]

<<<<<<< HEAD
    # Get approval gate
    res_get = client.get(f"/api/v1/approvals/{approval_id}", headers={"Authorization": "Bearer test-token"})
=======
    res_get = client.get(f"{settings.API_V1_STR}/approvals/{approval_id}")
>>>>>>> origin/main
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    # Decide approval
    res_decide = client.post(
<<<<<<< HEAD
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved"},
        headers={"Authorization": "Bearer test-token"}
=======
        f"{settings.API_V1_STR}/approvals/{approval_id}/decision",
        json={"decision": "approved"},
>>>>>>> origin/main
    )
    assert res_decide.status_code == 200
    assert res_decide.json()["status"] == "approved"
