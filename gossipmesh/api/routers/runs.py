from typing import BaseModel, List
import datetime

from gossipmesh.api import deps
<<<<<<< HEAD
from gossipmesh.api.errors import handle_exceptions
from gossipmesh.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
=======
from gossipmesh.api.deps import get_db
>>>>>>> b9bd3f04893d5e47964258f0651333180623246a

router = APIRouter(prefix="/runs", tags=["runs"])

class Run(BaseModel):
    repository: str
    issue: int
    pr: int
    workflow_type: str
    run_id: str
    status: str
    start_time: datetime
    end_time: datetime
    failure_reason: str
    branch: str
    commit_sha: str
    files_changed: List[str]
    model: str
    token_usage: int
    estimated_cost: float

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
# Dependency to get the database session
=======
>>>>>>> b9bd3f04893d5e47964258f0651333180623246a
@router.post("/")
def track_run(run: Run, db: Session = Depends(get_db)):
=======
=======
>>>>>>> b7b8fe0218e4445c90d5bb67c2cf017b66cdd67f
@router.dependency
def get_db_session(db: Session = Depends(get_db)):
    return db

@handle_exceptions
def track_run(run: Run, db: Session = Depends(get_db_session)):
<<<<<<< HEAD
>>>>>>> b7b8fe0218e4445c90d5bb67c2cf017b66cdd67f
=======
>>>>>>> b7b8fe0218e4445c90d5bb67c2cf017b66cdd67f
=======
@router.post("/")
def track_run(run: Run, db: Session = Depends(get_db)):
>>>>>>> b9bd3f04893d5e47964258f0651333180623246a
    # Implement logic to track the run details in the database
    # This is a placeholder, replace with actual database interaction code
    print(f"Tracking run: {{run}}")
