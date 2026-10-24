from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from gossipmesh.models.organization import Organization
from gossipmesh.models.webhook_event import WebhookEvent
