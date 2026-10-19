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

    id: int
    workflow_id: Optional[int]
    repository_id: Optional[int]
    action_type: str
    status: str
    diff_content: Optional[str]
    commit_sha: Optional[str]
    approver_id: Optional[int]
    approved_at: Optional[datetime]
    expires_at: datetime
    created_at: datetime


@router.post("/", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
def create_approval_gate(
    req: ApprovalCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=req.expires_in_hours)
    gate = ApprovalGate(
        workflow_id=req.workflow_id,
        repository_id=req.repository_id,
        action_type=req.action_type,
        status="pending",
        diff_content=req.diff_content,
        commit_sha=req.commit_sha,
        expires_at=expires_at,
    )
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return gate


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval_gate(
    approval_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    gate = db.query(ApprovalGate).filter(ApprovalGate.id == approval_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Approval gate not found")

    expires_at = gate.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if gate.status == "pending" and expires_at < datetime.now(timezone.utc):
        gate.status = "expired"
        db.commit()
        db.refresh(gate)

    return gate


@router.post("/{approval_id}/decision", response_model=ApprovalResponse)
def decide_approval(
    approval_id: int,
    req: ApprovalDecisionRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    gate = db.query(ApprovalGate).filter(ApprovalGate.id == approval_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Approval gate not found")

    if gate.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval gate is already {gate.status}")

    expires_at = gate.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        gate.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Approval gate has expired")

    if req.decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid decision. Must be 'approved' or 'rejected'")

    gate.status = req.decision
    gate.approver_id = current_user.id
    if req.decision == "approved":
        gate.approved_at = datetime.now(timezone.utc)
        if gate.workflow_id:
            wm = WorkflowManager(db)
            wm.approve_patch(gate.workflow_id, actor_id=current_user.id)

    db.commit()
    db.refresh(gate)
    return gate
