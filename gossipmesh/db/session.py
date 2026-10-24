from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.core.config import settings
import os

if os.environ.get("ENVIRONMENT") == "test":
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    from gossipmesh.models.base import Base

    # Import all models to ensure they are registered with Base.metadata
    from gossipmesh.models.user import User, UserGitHubCredential
    from gossipmesh.models.organization import Organization, UserOrganization, OrganizationInvitation
    from gossipmesh.models.project import Project
    from gossipmesh.models.audit import AuditEvent
    from gossipmesh.models.provider import ProviderCredential
    from gossipmesh.models.repository import Repository, IndexState
    from gossipmesh.models.runtime import Workflow, Job, Budget, Artifact
    from gossipmesh.models.service_account import ServiceAccount, APIKey
    from gossipmesh.models.finding import Finding
    from gossipmesh.models.review import ReviewResult
    from gossipmesh.models.usage import UsageRecord
    from gossipmesh.models.gossip import GossipMessageModel, GossipHeartbeat

    Base.metadata.create_all(bind=engine)
else:
    engine = create_engine(
        str(settings.DATABASE_URI),
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
