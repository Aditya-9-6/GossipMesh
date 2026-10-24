from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from gossipmesh.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=True)  # made nullable because of github login
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)
    mfa_recovery_codes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    github_user_id = Column(Integer, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
