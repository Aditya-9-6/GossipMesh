from fastapi import APIRouter, Depends
from typing import Any
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/")
def list_approvals(current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)) -> Any:
    return {"approvals": []}
