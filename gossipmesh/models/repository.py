from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy import JSON
from gossipmesh.models.base import Base


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    installation_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    account_name: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)  # 'Organization' or 'User'
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)  # GitHub's account ID
    repository_selection: Mapped[str] = mapped_column(String, nullable=False)  # 'all' or 'selected'
    permissions: Mapped[dict] = mapped_column(JSON, nullable=False)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_by: Mapped[str | None] = mapped_column(String, nullable=True)

    organization = relationship("Organization")


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


class IndexState(Base):
    __tablename__ = "index_states"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"), unique=True, nullable=False)
    last_commit_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, indexing, completed, failed

    repository = relationship("Repository")
