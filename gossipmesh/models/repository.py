from enum import Enum
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from gossipmesh.models.base import Base


class IndexStateEnum(str, Enum):
    PENDING = "pending"
    INDEXED = "indexed"


class RepositoryPolicy(Base):
    __tablename__ = "repository_policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True, nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    policy_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    auto_fix_enabled: Mapped[bool] = mapped_column(default=True)
    require_review: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_merge_passing: Mapped[bool] = mapped_column(Boolean, default=False)

    repository = relationship("Repository", back_populates="policy")


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"

    pass


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    __mapper_args__ = {"version_id_col": version_id}
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    default_branch: Mapped[str] = mapped_column(String, default="main")

    organization = relationship("Organization")
    project = relationship("Project", back_populates="repositories")
    policy = relationship("RepositoryPolicy", back_populates="repository", uselist=False)


class IndexState(Base):
    __tablename__ = "index_states"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True, nullable=False)
    last_commit_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, indexing, completed, failed

    repository = relationship("Repository")
