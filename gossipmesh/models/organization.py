from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from gossipmesh.models.base import Base

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    users = relationship("UserOrganization", back_populates="organization")
    owner = relationship("User")
    projects = relationship("Project", back_populates="organization")

class UserOrganization(Base):
    __tablename__ = "user_organizations"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="member") # admin, member, owner
    status: Mapped[str] = mapped_column(String, nullable=False, default="active") # active, invited, suspended

    user = relationship("User", back_populates="organizations")
    organization = relationship("Organization", back_populates="users")
