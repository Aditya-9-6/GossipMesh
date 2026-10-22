import hashlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, OrganizationRole, UserOrganization
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository
from gossipmesh.models.audit import AuditEvent
from gossipmesh.enterprise.disaster_recovery import DisasterRecoveryService
from gossipmesh.core.exceptions import ValidationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="TenantDR")
    user_org = UserOrganization(user_id=10, organization_id=1, role=OrganizationRole.owner)
    project = Project(id=1, name="core-app", organization_id=1)
    repo = Repository(id=1, name="backend", full_name="TenantDR/backend", github_id=999, organization_id=1)

    session.add_all([org, user_org, project, repo])
    session.commit()

    yield session
    session.close()


def test_tenant_data_export(db_session):
    data = DisasterRecoveryService.export_tenant_data(db_session, organization_id=1)

    assert data["organization"]["id"] == 1
    assert data["organization"]["name"] == "TenantDR"
    assert len(data["members"]) == 1
    assert data["members"][0]["user_id"] == 10
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "core-app"
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["github_id"] == 999
    assert "exported_at" in data

    with pytest.raises(ValidationError):
        DisasterRecoveryService.export_tenant_data(db_session, organization_id=9999)


def test_tenant_soft_delete_and_retention(db_session):
    org = DisasterRecoveryService.soft_delete_tenant(
        db_session,
        organization_id=1,
        actor_id=10,
        retention_days=45,
    )

    assert org.deleted_at is not None
    assert org.deleted_by == 10
    assert org.retention_days == 45

    audit = db_session.query(AuditEvent).filter_by(action="organization.soft_deleted").first()
    assert audit is not None
    assert audit.organization_id == 1
    assert audit.details["retention_days"] == 45


def test_backup_integrity_verification():
    raw_backup_data = b"PostgreSQL database dump snapshot 2026-10-21 v1"
    correct_hash = hashlib.sha256(raw_backup_data).hexdigest()

    # Valid backup
    assert DisasterRecoveryService.verify_backup_integrity(raw_backup_data, correct_hash) is True

    # Tampered or corrupted backup
    corrupted_data = b"PostgreSQL database dump snapshot 2026-10-21 v1 [CORRUPTED]"
    assert DisasterRecoveryService.verify_backup_integrity(corrupted_data, correct_hash) is False
