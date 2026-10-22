import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.audit import AuditEvent
from gossipmesh.enterprise.feature_flags import FeatureFlagKey, FeatureFlagService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_default_feature_flag_evaluation():
    service = FeatureFlagService()

    assert service.is_enabled(organization_id=1, flag=FeatureFlagKey.AUTONOMOUS_REVIEW) is True
    assert service.is_enabled(organization_id=1, flag=FeatureFlagKey.SECURITY_SCANNING) is True
    assert service.is_enabled(organization_id=1, flag=FeatureFlagKey.AST_INDEXING) is True
    assert service.is_enabled(organization_id=1, flag=FeatureFlagKey.BETA_PROVIDERS) is False


def test_organization_scoped_flag_override(db_session):
    service = FeatureFlagService()

    # Enable beta_providers for Org 1 only
    service.set_organization_flag(
        session=db_session,
        organization_id=1,
        flag=FeatureFlagKey.BETA_PROVIDERS,
        enabled=True,
        actor_id=10,
    )

    assert service.is_enabled(organization_id=1, flag=FeatureFlagKey.BETA_PROVIDERS) is True
    assert service.is_enabled(organization_id=2, flag=FeatureFlagKey.BETA_PROVIDERS) is False

    # Audit event recorded
    audit = db_session.query(AuditEvent).filter_by(action="feature_flag.org_override_set").first()
    assert audit is not None
    assert audit.organization_id == 1


def test_global_emergency_kill_switch_overrides_all(db_session):
    service = FeatureFlagService()

    # Org 1 has patch_generation explicitly enabled
    service.set_organization_flag(db_session, 1, FeatureFlagKey.PATCH_GENERATION, True)
    assert service.is_enabled(1, FeatureFlagKey.PATCH_GENERATION) is True

    # Emergency kill switch activated globally
    service.emergency_disable_globally(
        session=db_session,
        flag=FeatureFlagKey.PATCH_GENERATION,
        actor_id=1,
        reason="Runaway diff generation anomaly detected",
    )

    # Immediately disabled for ALL orgs
    assert service.is_enabled(1, FeatureFlagKey.PATCH_GENERATION) is False
    assert service.is_enabled(2, FeatureFlagKey.PATCH_GENERATION) is False

    # Lifting emergency restores functionality
    service.lift_global_emergency_disable(FeatureFlagKey.PATCH_GENERATION)
    assert service.is_enabled(1, FeatureFlagKey.PATCH_GENERATION) is True
