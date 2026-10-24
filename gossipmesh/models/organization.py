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


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer)
    email = Column(String)
    role = Column(String)
    token = Column(String, unique=True, index=True)
    is_accepted = Column(Boolean, default=False)


class OrganizationSAMLConfig(Base):
    __tablename__ = "organization_saml_configs"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, unique=True, index=True)
    entity_id = Column(String)
    sso_url = Column(String)
    x509_cert = Column(String)


class OrganizationRole:
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    organization_admin = "admin"
    developer = "developer"
