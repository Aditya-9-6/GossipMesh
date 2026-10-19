import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from gossipmesh.api import app
from gossipmesh.models.base import Base
from gossipmesh.api.deps import get_current_user
from gossipmesh.models.user import User
<<<<<<< HEAD

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

=======
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
>>>>>>> origin/main


def override_get_current_user():
<<<<<<< HEAD
    return User(id=1, email="test@gossipmesh.com", is_active=True)


app.dependency_overrides[get_current_user] = override_get_current_user
=======
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
    Base.metadata.create_all(bind=engine)
    response = client.post(
        f"{settings.API_V1_STR}/approvals/",
        json={
            "action_type": "push_commit",
            "diff_content": "--- a/file.py\n+++ b/file.py\n+print('hello')",
            "commit_sha": "abc1234",
            "expires_in_hours": 1,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["action_type"] == "push_commit"
    assert data["status"] == "pending"

<<<<<<< HEAD
    approval_id = data["id"]
    response_decide = client.post(
        f"/api/v1/approvals/{approval_id}/decide",
        json={"decision": "approved", "reason": "Looks good"}
=======
    res_get = client.get(f"{settings.API_V1_STR}/approvals/{approval_id}")
    assert res_get.status_code == 200
    assert res_get.json()["status"] == "pending"

    res_decide = client.post(
        f"{settings.API_V1_STR}/approvals/{approval_id}/decision",
        json={"decision": "approved"},
>>>>>>> origin/main
    )
    assert response_decide.status_code == 200
    assert response_decide.json()["status"] == "approved"
