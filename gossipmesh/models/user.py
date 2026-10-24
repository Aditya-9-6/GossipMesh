from typing import Optional
from sqlalchemy import Column, String, Boolean, Integer
from gossipmesh.models.base import Base


class UserGitHubCredential:
    pass


class UserOIDCCredential:
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=True)
    mfa_secret = Column(String(255), nullable=True)
    mfa_recovery_codes = Column(String(1024), nullable=True)
