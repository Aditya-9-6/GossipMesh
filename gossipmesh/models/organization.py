from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from gossipmesh.db.base_class import Base


class OrganizationRole(str, Enum):
    owner = "owner"
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    installation_id = Column(Integer, unique=True, nullable=False)
    account_login = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    permissions = Column(Text, nullable=True)
    events = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    organization = relationship("Organization", back_populates="github_installations")


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    members = relationship("UserOrganization", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="organization", cascade="all, delete-orphan")
    saml_config = relationship(
        "OrganizationSAMLConfig", back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )
    github_installations = relationship(
        "GithubAppInstallation", back_populates="organization", cascade="all, delete-orphan"
    )


class UserOrganization(Base):
    __tablename__ = "user_organizations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role = Column(String, default=OrganizationRole.developer.value, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="members")


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default=OrganizationRole.developer.value, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization")
