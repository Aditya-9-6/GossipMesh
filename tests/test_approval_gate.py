import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.api.main import app, get_db, get_current_user
from gossipmesh.models.base import Base
from gossipmesh.models.user import User
from gossipmesh.models.approval import ApprovalGateModel

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
        user = User(username="admin_test", role="admin", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()
    return user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_approval_gate_lifecycle():
    db = TestingSessionLocal()
    # Ensure test user exists
    user = db.query(User).filter(User.username == "admin_test").first()
    if not user:
        user = User(username="admin_test", role="admin", is_active=True)
        db.add(user)
        db.commit()
    db.close()

    # Test initial status or submission
    payload_data = {"action": "deploy_cluster", "target": "us-west-2"}
    response = client.post("/api/v1/approval/submit", json=payload_data)
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data or "status" in data
