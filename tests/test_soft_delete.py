import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.audit import AuditEvent

# Create engine and tables
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

@pytest.fixture
def session():
    with Session(engine) as session:
        yield session

def test_soft_delete_mixin_columns():
    org = Organization(name="Test Org")
    assert hasattr(org, "deleted_at")
    assert hasattr(org, "deleted_by")
    assert hasattr(org, "retention_days")

def test_active_query_helper_and_default_exclusion(session):
    org1 = Organization(name="Active Org")
    org2 = Organization(name="Deleted Org")
    session.add_all([org1, org2])
    session.commit()

    org2.soft_delete(session=session, actor_id=1)
    session.commit()

    # Test default exclusion via event listener
    orgs = session.scalars(select(Organization)).all()
    assert len(orgs) == 1
    assert orgs[0].name == "Active Org"

    # Test inclusion with execution option
    all_orgs = session.scalars(select(Organization).execution_options(include_deleted=True)).all()
    assert len(all_orgs) == 2

def test_soft_delete_method(session):
    org = Organization(name="Test Org 2")
    session.add(org)
    session.commit()

    org.soft_delete(session=session, actor_id=42, retention_days=30)
    session.commit()

    assert org.deleted_at is not None
    assert org.deleted_by == 42
    assert org.retention_days == 30

    # Look up audit event manually
    audit = session.scalars(select(AuditEvent).filter_by(action="organization_deleted", actor_id=42)).first()
    assert audit is not None
    assert audit.organization_id == org.id
    assert audit.details["model"] == "Organization"
    assert audit.details["id"] == org.id
    assert audit.details["retention_days"] == 30
