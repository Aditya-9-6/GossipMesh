from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from gossipmesh.db.base_class import Base


class OrganizationRole(str, Enum):
    owner = "owner"
    admin = "admin"
    developer = "developer"
    member = "member"


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    members = relationship("UserOrganization", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    repositories = relationship("Repository", back_populates="organization", cascade="all, delete-orphan")
    webhook_events = relationship("WebhookEvent", back_populates="organization", cascade="all, delete-orphan")


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    role = Column(String, default=OrganizationRole.member)
    is_suspended = Column(Boolean, default=False)

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="members")


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String, index=True, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default=OrganizationRole.developer)
    created_at = Column(DateTime, nullable=True)

    organization = relationship("Organization")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="webhook_events")
