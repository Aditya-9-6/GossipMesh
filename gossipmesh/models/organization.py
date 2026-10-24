from sqlalchemy import Column, Integer, String
from gossipmesh.db.base_class import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    organization_id = Column(Integer, index=True)
    role = Column(String)


class OrganizationRole:
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, index=True)
    email = Column(String, index=True)
    role = Column(String)
    token = Column(String, unique=True, index=True)
    status = Column(String, default="pending")
