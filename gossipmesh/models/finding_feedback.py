"""SQLAlchemy Model for Human Feedback Learning on Review Findings (Task 74)."""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from gossipmesh.models.base import Base


class FeedbackType(str, Enum):
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    REOPENED = "REOPENED"
    CORRECTED = "CORRECTED"


class FindingFeedback(Base):
    """
    Persisted human feedback on automated code review findings.
    Used for precision/recall evaluation and safe prompt enhancement without injection.
    """

    __tablename__ = "finding_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String(128), nullable=False, index=True)
    repository_id = Column(String(128), nullable=False, index=True)
    finding_fingerprint = Column(String(64), nullable=False, index=True)

    feedback_type = Column(String(32), nullable=False, default=FeedbackType.ACCEPTED.value, index=True)
    user_id = Column(String(128), nullable=True)
    user_comment = Column(Text, nullable=True)

    corrected_severity = Column(String(32), nullable=True)
    corrected_category = Column(String(64), nullable=True)
    file_path = Column(String(512), nullable=True)
    rule_id = Column(String(128), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "repository_id": self.repository_id,
            "finding_fingerprint": self.finding_fingerprint,
            "feedback_type": self.feedback_type,
            "user_id": self.user_id,
            "user_comment": self.user_comment,
            "corrected_severity": self.corrected_severity,
            "corrected_category": self.corrected_category,
            "file_path": self.file_path,
            "rule_id": self.rule_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
