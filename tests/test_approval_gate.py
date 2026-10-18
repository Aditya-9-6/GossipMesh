import pytest
from fastapi import FastAPI, HTTPException, Depends
from fastapi.testclient import TestClient

app = FastAPI()

approval_state = {"approved": False, "pending_payload": None}

@app.post("/gate/submit")
async def submit_payload(payload: dict):
    approval_state["pending_payload"] = payload
    approval_state["approved"] = False
    return {"status": "pending", "payload": payload}

@app.post("/gate/approve")
async def approve_payload():
    if approval_state["pending_payload"] is None:
        raise HTTPException(status_code=400, detail="No pending payload to approve")
    approval_state["approved"] = True
    return {"status": "approved", "payload": approval_state["pending_payload"]}

@app.get("/gate/status")
async def get_status():
    return approval_state

client = TestClient(app)

def test_approval_gate_lifecycle():
    # Test initial status
    response = client.get("/gate/status")
    assert response.status_code == 200
    data = response.json()
    assert data["approved"] is False
    assert data["pending_payload"] is None

    # Submit payload
    payload_data = {"action": "deploy_cluster", "target": "us-west-2"}
    response = client.post("/gate/submit", json=payload_data)
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # Verify status is pending
    response = client.get("/gate/status")
    assert response.json()["approved"] is False
    assert response.json()["pending_payload"] == payload_data

    # Approve payload
    response = client.post("/gate/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    # Verify final approved status
    response = client.get("/gate/status")
    assert response.json()["approved"] is True
    assert response.json()["pending_payload"] == payload_data
