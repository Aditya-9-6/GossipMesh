from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from gossipmesh.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id = Column(Integer, nullable=True)
    github_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    default_branch = Column(String, default="main", nullable=False)

    policy = relationship("RepositoryPolicy", back_populates="repository", uselist=False)


class RepositoryPolicy(Base):
    __tablename__ = "repository_policies"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False, unique=True)
    branch_protection_enabled = Column(Boolean, default=True)
    auto_merge_enabled = Column(Boolean, default=False)
    require_review_approval = Column(Boolean, default=True)
    min_approvals = Column(Integer, default=1)
    allowed_target_branches = Column(JSON, default=list)
    max_diff_lines = Column(Integer, default=500)
    scan_frequency_hours = Column(Integer, default=24)
    custom_rules = Column(JSON, default=dict)

    repository = relationship("Repository", back_populates="policy")


class IndexState(Base):
    __tablename__ = "index_states"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    branch = Column(String, default="main")
    last_indexed_sha = Column(String, nullable=True)
