from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from gossipmesh.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=True)  # made nullable because of github login
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    organizations = relationship("UserOrganization", back_populates="user")
    github_credential = relationship("UserGitHubCredential", back_populates="user", uselist=False)
    oidc_credentials = relationship("UserOIDCCredential", back_populates="user")


class UserOIDCCredential(Base):
    __tablename__ = "user_oidc_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sub: Mapped[str] = mapped_column(String, index=True, nullable=False)
    issuer: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    encrypted_id_token: Mapped[str | None] = mapped_column(String, nullable=True)

    user = relationship("User", back_populates="oidc_credentials")


class UserGitHubCredential(Base):
    __tablename__ = "user_github_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="github_credential")
