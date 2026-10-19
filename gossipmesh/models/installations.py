from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from gossipmesh.models.base import Base

class GithubAppInstallation(Base):
    __tablename__ = "github_app_installations"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, unique=True, index=True, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    account_name = Column(String, nullable=False)
    target_type = Column(String, nullable=True)
