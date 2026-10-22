import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository
from gossipmesh.models.runtime import Job, Workflow
from gossipmesh.models.audit import AuditEvent
from gossipmesh.enterprise.break_glass import BreakGlassControlService
from gossipmesh.enterprise.support_tooling import CustomerSupportTooling
from gossipmesh.core.exceptions import AuthorizationError, ValidationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="ClientOrg")
    repo = Repository(id=1, name="web", full_name="ClientOrg/web", github_id=901, organization_id=1)
    wf_failed = Workflow(id=10, organization_id=1, repository_id=1, status="failed")
    job_failed = Job(id=101, workflow_id=10, agent_name="reviewer", status="failed")

    session.add_all([org, repo, wf_failed, job_failed])
    session.commit()

    yield session
    session.close()


def test_support_tooling_requires_break_glass(db_session):
    bg_service = BreakGlassControlService()
    tooling = CustomerSupportTooling(break_glass_service=bg_service)

    # Without break-glass session -> blocked
    with pytest.raises(AuthorizationError):
        tooling.lookup_organization(db_session, support_user_id=99, organization_id=1)


def test_support_tooling_authorized_operations(db_session):
    bg_service = BreakGlassControlService()
    tooling = CustomerSupportTooling(break_glass_service=bg_service)

    # Grant break-glass session
    bg_service.request_access(
        session=db_session,
        support_user_id=99,
        organization_id=1,
        reason="Assisting customer with failed review workflow #10",
        ticket_id="SUP-8899",
    )

    # 1. Organization lookup
    info = tooling.lookup_organization(db_session, support_user_id=99, organization_id=1)
    assert info["id"] == 1
    assert info["name"] == "ClientOrg"

    # 2. Inspect health
    health = tooling.inspect_health(db_session, support_user_id=99, organization_id=1)
    assert health["failed_workflows_count"] == 1
    assert health["status"] == "degraded"

    # 3. Retry failed workflow
    retried_wf = tooling.retry_failed_workflow(db_session, support_user_id=99, organization_id=1, workflow_id=10)
    assert retried_wf.status == "pending"

    # Associated job set back to pending
    job = db_session.get(Job, 101)
    assert job.status == "pending"

    # 4. Initiate export
    export_pkg = tooling.initiate_export(db_session, support_user_id=99, organization_id=1)
    assert export_pkg["organization"]["name"] == "ClientOrg"

    # Audit events verified
    events = db_session.query(AuditEvent).filter_by(actor_id=99).all()
    actions = {e.action for e in events}
    assert "support.organization_lookup" in actions
    assert "support.workflow_retried" in actions
