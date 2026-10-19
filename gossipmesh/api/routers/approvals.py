from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.approval import ApprovalGate
from gossipmesh.runtime.workflow import WorkflowManager

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


class ApprovalCreateRequest(BaseModel):
    workflow_id: Optional[int] = None
    repository_id: Optional[int] = None
    action_type: str
    diff_content: Optional[str] = None
    commit_sha: Optional[str] = None
    expires_in_hours: int = 24


class ApprovalDecisionRequest(BaseModel):
    decision: str


class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: Optional[int] = None
    repository_id: Optional[int] = None
    action_type: str
    status: str
    diff_content: Optional[str] = None
    commit_sha: Optional[str] = None
    approver_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime


@router.post("/", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
def create_approval_gate(
    req: ApprovalCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    gate = ApprovalGate(
        name=f"Approval {req.action_type}",
        description=req.diff_content,
        is_active=True,
    )
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return gate


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval_gate(
    approval_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    gate = db.query(ApprovalGate).filter(ApprovalGate.id == approval_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Approval gate not found")
    return gate


@router.post("/{approval_id}/decision", response_model=ApprovalResponse)
def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    gate = db.query(ApprovalGate).filter(ApprovalGate.id == approval_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Approval gate not found")

    if req.decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid decision. Must be 'approved' or 'rejected'")

    db.commit()
    db.refresh(gate)
    return gate
