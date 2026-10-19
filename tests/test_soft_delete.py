import unittest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization
from gossipmesh.models.audit import AuditEvent

class TestSoftDelete(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_soft_delete_mixin_columns(self):
        org = Organization(name="Test Org")
        self.assertTrue(hasattr(org, "deleted_at"))
        self.assertTrue(hasattr(org, "deleted_by"))
        self.assertTrue(hasattr(org, "retention_days"))

    def test_active_query_helper_and_default_exclusion(self):
        org1 = Organization(name="Active Org")
        org2 = Organization(name="Deleted Org")
        self.session.add_all([org1, org2])
        self.session.commit()

        org2.soft_delete(session=self.session, actor_id=1)
        self.session.commit()

        # Test default exclusion via event listener
        orgs = self.session.scalars(select(Organization)).all()
        self.assertEqual(len(orgs), 1)
        self.assertEqual(orgs[0].name, "Active Org")

        # Test inclusion with execution option
        all_orgs = self.session.scalars(select(Organization).execution_options(include_deleted=True)).all()
        self.assertEqual(len(all_orgs), 2)

    def test_soft_delete_method(self):
        org = Organization(name="Test Org 2")
        self.session.add(org)
        self.session.commit()

        org.soft_delete(session=self.session, actor_id=42, retention_days=30)
        self.session.commit()

        self.assertIsNotNone(org.deleted_at)
        self.assertEqual(org.deleted_by, 42)
        self.assertEqual(org.retention_days, 30)

        # Look up audit event manually
        audit = self.session.scalars(select(AuditEvent).filter_by(action="organization_deleted", actor_id=42)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.organization_id, org.id)
        self.assertEqual(audit.details["model"], "Organization")
        self.assertEqual(audit.details["id"], org.id)
        self.assertEqual(audit.details["retention_days"], 30)

if __name__ == "__main__":
    unittest.main()
