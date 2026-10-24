from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from gossipmesh.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)  # made nullable because of github login
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enabled: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_recovery_codes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organizations = relationship("UserOrganization", back_populates="user")
    github_credential = relationship("UserGitHubCredential", back_populates="user", uselist=False)
    oidc_credentials = relationship("UserOIDCCredential", back_populates="user")


class UserGitHubCredential(Base):
    __tablename__ = "user_github_credentials"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    github_user_id = Column(Integer, unique=True, index=True, nullable=False)
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="github_credential")


class UserOIDCCredential(Base):
    __tablename__ = "user_oidc_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    sub: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    encrypted_id_token: Mapped[str | None] = mapped_column(String, nullable=True)
    access_token = Column(String(1024), nullable=True)
    refresh_token = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="oidc_credentials")
