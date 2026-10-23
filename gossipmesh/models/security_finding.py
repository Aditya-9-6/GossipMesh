from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from gossipmesh.models.base import Base


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    category = Column(String, nullable=True)
    rule_id = Column(String, nullable=True)
    sources = Column(JSON, default=list)
    severity = Column(String, default="medium")
    message = Column(String, nullable=False)

    repository = relationship("Repository")
