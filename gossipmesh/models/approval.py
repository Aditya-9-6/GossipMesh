from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from gossipmesh.models.base import Base

class ApprovalGate(Base):
    __tablename__ = "approval_gates"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    action_type = Column(String(50), nullable=False)
    diff_content = Column(Text, nullable=True)
    commit_sha = Column(String(64), nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    expires_in_hours = Column(Integer, default=24, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    approver = relationship("User", foreign_keys=[approver_id])
    workflow = relationship("Workflow", foreign_keys=[workflow_id])
    repository = relationship("Repository", foreign_keys=[repository_id])
