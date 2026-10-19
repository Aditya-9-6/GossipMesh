from typing import List
import datetime

from gossipmesh.api.errors import handle_exceptions
from gossipmesh.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

router = APIRouter(prefix="/runs", tags=["runs"])

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
    files_changed: List[str]
    model: str
    token_usage: int
    estimated_cost: float

@router.post("/")
@handle_exceptions
def track_run(run: Run, db: Session = Depends(get_db)):
    print(f"Tracking run: {run}")
    return {
        "message": "Run tracked successfully"
    }
