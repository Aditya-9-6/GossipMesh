from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from gossipmesh.models.base import Base


class ReviewResult(Base):
    __tablename__ = "review_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workflow_id: Mapped[int | None] = mapped_column(ForeignKey("workflows.id"), nullable=True, index=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    verdict: Mapped[str] = mapped_column(String, nullable=False)  # e.g. approved, rejected, neutral
    summary: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("Workflow")
