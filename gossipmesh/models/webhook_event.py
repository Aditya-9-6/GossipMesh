from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime, timezone
from gossipmesh.db.base_class import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)
    event_type = Column(String, index=True)
    payload = Column(JSON)
    status = Column(String, default="pending", index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)
