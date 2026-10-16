from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from gossipmesh.models.base import Base
from gossipmesh.models.mixins import SoftDeleteMixin

class BackgroundJob(SoftDeleteMixin, Base):
    __tablename__ = "background_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    task_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, running, success, failed, dead_letter, cancelled
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_identity: Mapped[str | None] = mapped_column(String, nullable=True)
    retries: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization = relationship("Organization")
    user = relationship("User")
