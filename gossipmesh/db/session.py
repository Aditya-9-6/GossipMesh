import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

database_url = os.getenv("DATABASE_URL", "sqlite:///:memory:")
if os.environ.get("ENVIRONMENT") == "test" or database_url.startswith("sqlite"):
    engine = create_engine(
        database_url if os.environ.get("ENVIRONMENT") != "test" else "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from gossipmesh.models.base import Base

    # Import all models to ensure they are registered with Base.metadata
    from gossipmesh.models.user import User, UserGitHubCredential
    from gossipmesh.models.organization import Organization, UserOrganization, OrganizationInvitation
    from gossipmesh.models.project import Project
    from gossipmesh.models.audit import AuditEvent
    from gossipmesh.models.provider import ProviderCredential
    from gossipmesh.models.repository import Repository, RepositoryPolicy, IndexState
    from gossipmesh.models.runtime import Workflow, Job, Budget, Artifact
    from gossipmesh.models.service_account import ServiceAccount, APIKey
    from gossipmesh.models.finding import Finding
    from gossipmesh.models.review import ReviewResult
    from gossipmesh.models.usage import UsageRecord
    from gossipmesh.models.gossip import GossipMessageModel, GossipHeartbeat

    Base.metadata.create_all(bind=engine)
else:
    try:
        engine = create_engine(database_url)
    except Exception:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from gossipmesh.db.base import Base
