from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import datetime

from gossipmesh.api import deps
from gossipmesh.api.deps import get_db

router = APIRouter(prefix="/runs", tags=["runs"])


# Model for run tracking
class Run(BaseModel):
    repository: str
    issue: int
    pr: int
    workflow_type: str
    run_id: str
    status: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    failure_reason: str
    branch: str
    commit_sha: str
    files_changed: list[str]
    model: str
    token_usage: int
    estimated_cost: float


@router.post("/")
def track_run(run: Run, db: Session = Depends(get_db)):
    # Implement logic to track the run details in the database
    # This is a placeholder, replace with actual database interaction code
    print(f"Tracking run: {{run}}")
    return {"message": "Run tracked successfully"}
