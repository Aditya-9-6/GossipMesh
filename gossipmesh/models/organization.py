from sqlalchemy import Column, Integer, String, Boolean
from gossipmesh.db.session import Base


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class UserOrganization(Base):
    __tablename__ = "user_organizations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    organization_id = Column(Integer)
    role = Column(String)
    is_suspended = Column(Boolean, default=False)


class OrganizationRole:
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
