import unittest
from gossipmesh.enterprise.canary import CanaryManager


class TestCanaryManager(unittest.TestCase):
    def test_is_automation_allowed_valid(self):
        manager = CanaryManager(allowed_repositories=["repo1", "repo2"], allowed_labels=["canary"])
        self.assertTrue(manager.is_automation_allowed("repo1", ["canary", "other"]))

    def test_is_automation_allowed_invalid_repo(self):
        manager = CanaryManager(allowed_repositories=["repo1"])
        self.assertFalse(manager.is_automation_allowed("repo2"))
        metrics = manager.get_metrics()
        self.assertEqual(metrics["runs_rejected_repo"], 1)

    def test_is_automation_allowed_invalid_label(self):
        manager = CanaryManager(allowed_labels=["canary"])
        self.assertFalse(manager.is_automation_allowed("repo1", ["prod"]))
        metrics = manager.get_metrics()
        self.assertEqual(metrics["runs_rejected_label"], 1)

    def test_daily_limits_enforcement(self):
        manager = CanaryManager(daily_limit=2)
        # Attempt to bypass limit via allowed requests
        manager.record_run()
        manager.record_run()

        self.assertFalse(manager.is_automation_allowed("repo1"))
        metrics = manager.get_metrics()
        self.assertEqual(metrics["runs_rejected_limit"], 1)

    def test_record_run(self):
        manager = CanaryManager(daily_limit=2)
        self.assertTrue(manager.record_run())
        self.assertTrue(manager.record_run())
        self.assertFalse(manager.record_run())

    def test_shutdown_triggers(self):
        manager = CanaryManager()
        self.assertTrue(manager.is_automation_allowed("repo1"))

        manager.shutdown()
        self.assertFalse(manager.is_automation_allowed("repo1"))
        metrics = manager.get_metrics()
        self.assertEqual(metrics["runs_rejected_shutdown"], 1)

    def test_unsafe_defaults(self):
        manager = CanaryManager()
        self.assertFalse(manager.allow_force_push)
        self.assertFalse(manager.allow_auto_merge)
        self.assertTrue(manager.require_human_approval)

    def test_metrics_tracking(self):
        manager = CanaryManager(allowed_repositories=["repo1"], allowed_labels=["canary"], daily_limit=1)

        # Valid
        manager.is_automation_allowed("repo1", ["canary"])
        manager.record_run()

        # Limit reached
        manager.is_automation_allowed("repo1", ["canary"])

        # Repo invalid
        manager.is_automation_allowed("repo2", ["canary"])

        # Label invalid
        manager.is_automation_allowed("repo1", ["prod"])

        metrics = manager.get_metrics()
        self.assertEqual(metrics["runs_attempted"], 4)
        self.assertEqual(metrics["runs_allowed"], 1)
        self.assertEqual(metrics["runs_rejected_limit"], 1)
        self.assertEqual(metrics["runs_rejected_repo"], 1)
        self.assertEqual(metrics["runs_rejected_label"], 1)


if __name__ == "__main__":
    unittest.main()
