from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from pydantic import BaseModel, ConfigDict
from gossipmesh.models.base import Base


class RepositoryPolicy(BaseModel):
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
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    github_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    full_name = Column(String(256), nullable=False, index=True)
    default_branch = Column(String(128), default="main", nullable=False)


class IndexState(Base):
    __tablename__ = "index_states"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, index=True)
    commit_sha = Column(String(64), nullable=False)
    status = Column(String(32), default="pending", nullable=False)
