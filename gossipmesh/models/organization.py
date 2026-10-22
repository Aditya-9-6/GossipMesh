import enum
from sqlalchemy import Boolean, ForeignKey, String, Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gossipmesh.models.base import Base
from gossipmesh.models.mixins import SoftDeleteMixin


class OrganizationRole(str, enum.Enum):
    owner = "owner"
    billing_admin = "billing_admin"
    organization_admin = "organization_admin"
    security_admin = "security_admin"
    developer = "developer"
    reviewer = "reviewer"
    auditor = "auditor"
    analyst = "analyst"
    service_account = "service_account"


class Organization(SoftDeleteMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    users = relationship("UserOrganization", back_populates="organization")
    owner = relationship("User")
    projects = relationship("Project", back_populates="organization")
    saml_config = relationship(
        "OrganizationSAMLConfig", back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    role: Mapped[OrganizationRole] = mapped_column(
        SQLAlchemyEnum(OrganizationRole), nullable=False, default=OrganizationRole.developer
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active, invited, suspended
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="users")


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    token: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    role: Mapped[OrganizationRole] = mapped_column(
        SQLAlchemyEnum(OrganizationRole), nullable=False, default=OrganizationRole.developer
    )

    organization = relationship("Organization")
