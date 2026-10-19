from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from gossipmesh.models.base import Base
import uuid

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type = Column(String(50), nullable=False)
    diff_content = Column(Text, nullable=False)
    commit_sha = Column(String(64), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    approver_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)


class ApprovalGate(Base):
    __tablename__ = "approval_gates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
