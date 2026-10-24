from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pydantic import BaseModel, ConfigDict
from gossipmesh.models.base import Base


class RepositoryPolicyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    branch_protection_enabled: bool = True
    auto_merge_enabled: bool = False
    require_review_approval: bool = True
    min_approvals: int = 1
    allowed_target_branches: List[str] = ["main", "master"]
    max_diff_lines: int = 500
    scan_frequency_hours: int = 24
    custom_rules: Dict[str, Any] = {}


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __mapper_args__ = {"version_id_col": version_id}
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    default_branch: Mapped[str] = mapped_column(String(128), default="main", nullable=False)

    organization = relationship("Organization")
    project = relationship("Project", back_populates="repositories")


class RepositoryPolicy(Base):
    __tablename__ = "repository_policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True, nullable=False)
    policy_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    repository = relationship("Repository")


class IndexState(Base):
    __tablename__ = "index_states"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    commit_sha = Column(String(64), nullable=False)
    status = Column(String(32), default="pending", nullable=False)
