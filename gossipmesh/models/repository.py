from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from gossipmesh.models.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    github_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, unique=True, index=True, nullable=False)
    default_branch = Column(String, default="main", nullable=False)

    organization = relationship("Organization", back_populates="repositories")
    project = relationship("Project", back_populates="repositories")
    policy = relationship("RepositoryPolicy", back_populates="repository", uselist=False)


class RepositoryPolicy(Base):
    __tablename__ = "repository_policies"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), unique=True, nullable=False)
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
    repository_id = Column(Integer, ForeignKey("repositories.id"), unique=True, nullable=False)
    last_indexed_at = Column(String, nullable=True)

    repository = relationship("Repository")


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    installation_id = Column(Integer, unique=True, nullable=False)
    account_login = Column(String, nullable=False)

    organization = relationship("Organization")
