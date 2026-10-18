import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.api import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

client = TestClient(app)


def test_approval_gate_lifecycle():
    Base.metadata.create_all(bind=engine)
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
    get_data = res_get.json()
    assert get_data["id"] == approval_id
