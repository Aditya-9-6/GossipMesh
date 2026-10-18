import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from gossipmesh.models.base import Base

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, index=True, nullable=False)
    diff_content = Column(Text, nullable=False)
    commit_sha = Column(String, index=True, nullable=False)
    status = Column(String, default="pending", index=True, nullable=False)
    expires_in_hours = Column(Integer, default=24, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    approver_id = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)

class ApprovalGate(Base):
    __tablename__ = "approval_gates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
