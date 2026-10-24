from typing import Any
from sqlalchemy.orm import declarative_base

Base: Any = declarative_base()

from gossipmesh.models.organization import Organization
from gossipmesh.models.webhook_event import WebhookEvent
from gossipmesh.models.user import User
from gossipmesh.models.repository import Repository
from gossipmesh.models.project import Project
from gossipmesh.models.session import UserSession
from gossipmesh.models.service_account import APIKey
