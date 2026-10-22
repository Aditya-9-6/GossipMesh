import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, OrganizationRole, UserOrganization
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository
from gossipmesh.models.runtime import Workflow
from gossipmesh.models.billing import UsageRecord
from gossipmesh.models.audit import AuditEvent
from gossipmesh.enterprise.disaster_recovery import DisasterRecoveryService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="PurgeCorp")
    user_org = UserOrganization(user_id=1, organization_id=1, role=OrganizationRole.owner)
    repo = Repository(id=1, name="app", full_name="PurgeCorp/app", github_id=555, organization_id=1)
    wf = Workflow(id=1, organization_id=1, repository_id=1, status="completed")
    usage = UsageRecord(id=1, organization_id=1, metric_type="reviewed_prs", quantity=1.0, idempotency_key="u1")

    session.add_all([org, user_org, repo, wf, usage])
    session.commit()

    yield session
    session.close()


def test_tenant_export_package(db_session):
    data = DisasterRecoveryService.export_tenant_data(db_session, organization_id=1)
    assert data["organization"]["name"] == "PurgeCorp"
    assert len(data["members"]) == 1
    assert len(data["repositories"]) == 1
    assert data["workflows_count"] == 1
    assert data["usage_records_count"] == 1


def test_tenant_full_purge(db_session):
    res = DisasterRecoveryService.purge_organization_data(db_session, organization_id=1, actor_id=1)

    assert res["repositories_deleted"] == 1
    assert res["workflows_deleted"] == 1
    assert res["usage_deleted"] == 1
    assert res["members_deleted"] == 1

    # Verify rows no longer exist
    assert db_session.query(Repository).filter_by(organization_id=1).count() == 0
    assert db_session.query(Workflow).filter_by(organization_id=1).count() == 0
    assert db_session.query(UsageRecord).filter_by(organization_id=1).count() == 0

    # Verify audit event emitted
    audit = db_session.query(AuditEvent).filter_by(action="organization.purged").first()
    assert audit is not None
    assert audit.organization_id == 1
