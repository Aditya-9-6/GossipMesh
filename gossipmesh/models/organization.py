"""
Organization Models.
"""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from gossipmesh.models.base import Base
import enum


class OrganizationRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, index=True)
    installation_id = Column(Integer, unique=True, index=True)
    account_name = Column(String)
    organization = relationship("Organization", back_populates="github_installations")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    github_installations = relationship("GithubAppInstallation", back_populates="organization")
    deleted_at = Column(Integer, nullable=True)
    deleted_by = Column(Integer, nullable=True)
    retention_days = Column(Integer, nullable=True, default=30)


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    organization_id = Column(Integer, index=True)
    role: OrganizationRole = Column(SQLEnum(OrganizationRole), default=OrganizationRole.developer)  # type: ignore
    is_suspended = Column(Boolean, default=False)
    organization = relationship("Organization")


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, index=True)
    email = Column(String, index=True)
    token = Column(String, unique=True, index=True)
    role: OrganizationRole = Column(SQLEnum(OrganizationRole), default=OrganizationRole.developer)  # type: ignore
