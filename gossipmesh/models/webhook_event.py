"""
Webhook event model.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from gossipmesh.db.base_class import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    event_type = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False)
