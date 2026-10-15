from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from gossipmesh.models.base import Base

from sqlalchemy import Boolean

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    users = relationship("UserOrganization", back_populates="organization")
    owner = relationship("User")
    projects = relationship("Project", back_populates="organization")
    saml_config = relationship("OrganizationSAMLConfig", back_populates="organization", uselist=False, cascade="all, delete-orphan")

class UserOrganization(Base):
    __tablename__ = "user_organizations"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="member") # admin, member, owner
    status: Mapped[str] = mapped_column(String, nullable=False, default="active") # active, invited, suspended
    role: Mapped[str] = mapped_column(String, nullable=False, default="member") # admin, member, etc
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="users")

class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="member")

    organization = relationship("Organization")
