from sqlalchemy import String, Date, Integer, ForeignKey, DateTime, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from gossipmesh.models.base import Base
from gossipmesh.models.mixins import SoftDeleteMixin


class Workflow(SoftDeleteMixin, Base):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __mapper_args__ = {"version_id_col": version_id}
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending, running, completed, failed, cancelled, blocked
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization = relationship("Organization")
    repository = relationship("Repository")
    jobs = relationship("Job", back_populates="workflow")


class Job(SoftDeleteMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __mapper_args__ = {"version_id_col": version_id}
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workflow = relationship("Workflow", back_populates="jobs")


class Budget(SoftDeleteMixin, Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), unique=True, nullable=False
    )
    monthly_limit_usd: Mapped[float] = mapped_column(Float, default=100.0)
    current_spend_usd: Mapped[float] = mapped_column(Float, default=0.0)

    organization = relationship("Organization")


class Artifact(SoftDeleteMixin, Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job")


class UsageLimit(SoftDeleteMixin, Base):
    __tablename__ = "usage_limits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    repository_id: Mapped[int | None] = mapped_column(
        ForeignKey("repositories.id"), nullable=True, index=True
    )

    daily_ai_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_prs_created: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_changed_lines: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_sandbox_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    organization = relationship("Organization")
    repository = relationship("Repository")


class DailyUsage(Base):
    __tablename__ = "daily_usages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    repository_id: Mapped[int | None] = mapped_column(
        ForeignKey("repositories.id"), nullable=True, index=True
    )
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)

    ai_runs: Mapped[int] = mapped_column(Integer, default=0)
    prs_created: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    changed_lines: Mapped[int] = mapped_column(Integer, default=0)
    sandbox_minutes: Mapped[int] = mapped_column(Integer, default=0)

    organization = relationship("Organization")
    repository = relationship("Repository")
