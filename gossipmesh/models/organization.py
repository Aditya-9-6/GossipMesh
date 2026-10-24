"""
Organization and related models.
"""

import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from gossipmesh.db.base_class import Base


class OrganizationRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    developer = "developer"
    member = "member"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)


class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    installation_id = Column(String(255), unique=True, index=True, nullable=False)
    account_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    organization = relationship("Organization", backref="github_installations")


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role = Column(String(50), nullable=False, default="member")
    is_suspended = Column(Boolean, default=False, nullable=False)

    organization = relationship("Organization", backref="user_memberships")


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role: str = Column(String(50), nullable=False, default="member")


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), nullable=False)
    role: str = Column(String(50), nullable=False, default="member")
    token = Column(String(255), unique=True, index=True, nullable=True)
