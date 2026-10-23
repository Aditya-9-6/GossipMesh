from typing import Optional, Any
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from gossipmesh.models.base import Base


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"

    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, unique=True, nullable=False, index=True)
    account_login = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    repositories = relationship("Repository", back_populates="installation", cascade="all, delete-orphan")

    def __init__(
        self,
        installation_id: int,
        account_login: str,
        account_type: str,
        target_type: str,
        **kwargs: Any,
    ) -> None:
        self.installation_id = installation_id
        self.account_login = account_login
        self.account_type = account_type
        self.target_type = target_type


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False, index=True)
    default_branch = Column(String, default="main")
    installation_id = Column(Integer, ForeignKey("github_app_installations.id"), nullable=True)
    organization_id = Column(Integer, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    installation = relationship("GithubAppInstallation", back_populates="repositories")
    policy = relationship("RepositoryPolicy", back_populates="repository", uselist=False, cascade="all, delete-orphan")
    project = relationship("Project", back_populates="repositories")

    def __init__(
        self,
        github_id: int,
        name: str,
        full_name: str,
        installation_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        project_id: Optional[int] = None,
        default_branch: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if id is not None:
            self.id = id
        self.github_id = github_id
        self.name = name
        self.full_name = full_name
        self.installation_id = installation_id
        self.organization_id = organization_id
        self.project_id = project_id
        if default_branch is not None:
            self.default_branch = default_branch


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

    def __init__(
        self, name: str, repository_id: Optional[int] = None, scan_frequency_hours: Optional[int] = 24, **kwargs: Any
    ) -> None:
        self.name = name
        if repository_id is not None:
            self.repository_id = repository_id
        self.scan_frequency_hours = scan_frequency_hours


class IndexState(Base):
    __tablename__ = "index_states"

    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, nullable=False, index=True)
    organization_id = Column(Integer, nullable=True)

    def __init__(self, installation_id: int, organization_id: Optional[int] = None, **kwargs: Any) -> None:
        self.installation_id = installation_id
        self.organization_id = organization_id
