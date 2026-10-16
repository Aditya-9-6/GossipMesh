import unittest
from gossipmesh.repository.github import GitHubIntegration
from gossipmesh.core.exceptions import AuthorizationError

class TestGitHubIntegration(unittest.TestCase):
    def test_sync_repository_insufficient_permissions(self):
        # Provide empty permissions to force AuthorizationError on sync_repository
        github_integration = GitHubIntegration(app_id="test_app_id", private_key="test_key", permissions={})

        with self.assertRaises(AuthorizationError) as context:
            github_integration.sync_repository("owner/repo", 123)

        self.assertIn("Missing required permission scope: 'metadata'", str(context.exception))

if __name__ == "__main__":
    unittest.main()
