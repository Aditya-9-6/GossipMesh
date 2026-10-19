from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

from gossipmesh.api.main import app
from gossipmesh.models.base import Base

# Initialize the database engine and session
engine = create_engine("sqlite:///:memory:", echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Create the database tables
Base.metadata.create_all(bind=engine)

# Create a test client for the FastAPI app
client = TestClient(app)

# Test case for tracking a run
def test_track_run():
    # Create a sample run data
    run_data = {
        "repository": "gossipmesh",
        "issue": 1,
        "pr": 2,
        "workflow_type": "CI",
        "run_id": "123456",
        "status": "success",
<<<<<<< HEAD
        "start_time": datetime.datetime(2024, 1, 1, 12, 0),
        "end_time": datetime.datetime(2024, 1, 1, 12, 30),
=======
        "start_time": datetime.datetime(2024, 1, 1, 12, 0).isoformat(),
        "end_time": datetime.datetime(2024, 1, 1, 12, 30).isoformat(),
>>>>>>> origin/main
        "failure_reason": "None",
        "branch": "main",
        "commit_sha": "abc123",
        "files_changed": ["file1.py", "file2.py"],
        "model": "gemini-2.5-flash",
        "token_usage": 1000,
        "estimated_cost": 0.01
    }

    # Send a POST request to track the run
<<<<<<< HEAD
    response = client.post("/runs/", json=run_data)
=======
    from gossipmesh.core.config import settings
    response = client.post(f"{settings.API_V1_STR}/runs/", json=run_data)
>>>>>>> origin/main

    # Assert that the response status code is 200 OK
    assert response.status_code == 200

    # Assert that the response message is correct
    assert response.json() == {
        "message": "Run tracked successfully"
    }
