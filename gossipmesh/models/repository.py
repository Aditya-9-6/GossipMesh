from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text, DateTime, JSON
from pydantic import BaseModel, ConfigDict
from gossipmesh.models.base import Base


class RepositoryPolicy(Base):
    __tablename__ = "repository_policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True, index=True, nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    policy_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    auto_fix_enabled: Mapped[bool] = mapped_column(default=True)
    require_review: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_merge_passing: Mapped[bool] = mapped_column(Boolean, default=False)
    branch_protection_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_merge_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_review_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_approvals: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    allowed_target_branches: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    max_diff_lines: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    scan_frequency_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    custom_rules: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="policy")


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    installation_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    repository_selection: Mapped[str] = mapped_column(String, nullable=False)
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    default_branch: Mapped[str] = mapped_column(String, default="main", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)

    organization = relationship("Organization")
    project = relationship("Project", back_populates="repositories")
    policy: Mapped[Optional["RepositoryPolicy"]] = relationship(
        "RepositoryPolicy", back_populates="repository", uselist=False, cascade="all, delete-orphan"
    )


class IndexState(Base):
    __tablename__ = "index_states"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
