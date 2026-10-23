from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from gossipmesh.models.base import Base


class ApprovalGate(Base):
    __tablename__ = "approval_gates"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True, index=True)
    action_type = Column(String(50), nullable=False)  # push_commit, create_pr, post_review, apply_patch
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected, expired
    diff_content = Column(Text, nullable=True)
    commit_sha = Column(String(100), nullable=True)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)
