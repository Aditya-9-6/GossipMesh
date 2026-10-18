import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.models.base import Base
from gossipmesh.models.runtime import UsageLimit, DailyUsage
from gossipmesh.runtime.usage import UsageManager
from gossipmesh.core.exceptions import UsageLimitError
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository

class TestUsageManager(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()

        # Add mock org and repo
        org = Organization(id=1, name="Test Org")
        self.session.add(org)
        repo = Repository(id=1, organization_id=1, github_id=101, name="repo1", full_name="Test Org/repo1")
        self.session.add(repo)
        self.session.commit()

        self.manager = UsageManager(self.session)

    def tearDown(self):
        self.session.close()

    def test_record_usage_within_limits(self):
        # Set limit
        limit = UsageLimit(organization_id=1, daily_ai_runs=5)
        self.session.add(limit)
        self.session.commit()

        # Record usage
        usage = self.manager.check_and_record_usage(organization_id=1, ai_runs=3)
        self.assertEqual(usage.ai_runs, 3)

        # Record again
        usage2 = self.manager.check_and_record_usage(organization_id=1, ai_runs=2)
        self.assertEqual(usage2.ai_runs, 5)

        # Verify DB
        db_usage = self.session.query(DailyUsage).filter_by(organization_id=1).first()
        self.assertEqual(db_usage.ai_runs, 5)

    def test_record_usage_exceeds_limits(self):
        # Set limit
        limit = UsageLimit(organization_id=1, daily_ai_runs=5)
        self.session.add(limit)
        self.session.commit()

        # Record usage that exceeds limit
        with self.assertRaises(UsageLimitError) as context:
            self.manager.check_and_record_usage(organization_id=1, ai_runs=6)

        self.assertIn("Daily AI runs limit exceeded", str(context.exception))

        # Verify no usage recorded in DB
        db_usage = self.session.query(DailyUsage).filter_by(organization_id=1).first()
        self.assertIsNone(db_usage)

    def test_record_usage_repo_limit(self):
        # Set org and repo limits
        org_limit = UsageLimit(organization_id=1, daily_tokens_used=1000)
        repo_limit = UsageLimit(organization_id=1, repository_id=1, daily_tokens_used=500)
        self.session.add_all([org_limit, repo_limit])
        self.session.commit()

        # Record repo usage within repo limit
        self.manager.check_and_record_usage(organization_id=1, repository_id=1, tokens_used=400)

        # Record repo usage exceeding repo limit
        with self.assertRaises(UsageLimitError):
            self.manager.check_and_record_usage(organization_id=1, repository_id=1, tokens_used=200)

        # Record org usage (no repo specified) within org limit
        self.manager.check_and_record_usage(organization_id=1, tokens_used=500)

        # Record org usage exceeding org limit
        with self.assertRaises(UsageLimitError):
            self.manager.check_and_record_usage(organization_id=1, tokens_used=200)

if __name__ == "__main__":
    unittest.main()
