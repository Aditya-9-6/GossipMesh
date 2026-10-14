import unittest
from unittest.mock import patch, MagicMock
from gossipmesh.repository.github import GitHubIntegration

class TestGitHubIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_rsa_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIBOQIBAAJAVY6qupT3\n-----END RSA PRIVATE KEY-----"
        self.github_integration = GitHubIntegration(app_id="12345", private_key=self.mock_rsa_key)

    def test_generate_installation_token(self):
        # the app_auth instance is created in __init__
        mock_installation_auth = MagicMock()
        mock_installation_auth.token = "fake-token"
        self.github_integration.app_auth = MagicMock()
        self.github_integration.app_auth.get_installation_auth.return_value = mock_installation_auth

        token = self.github_integration.generate_installation_token(100)

        self.github_integration.app_auth.get_installation_auth.assert_called_once_with(100)
        self.assertEqual(token, "fake-token")

    @patch("gossipmesh.repository.github.GitHubIntegration.get_installation_client")
    def test_validate_repository_access_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_client.get_repo.return_value = mock_repo

        result = self.github_integration.validate_repository_access(100, "test-org/test-repo")

        mock_get_client.assert_called_once_with(100)
        mock_client.get_repo.assert_called_once_with("test-org/test-repo")
        self.assertTrue(result)

    @patch("gossipmesh.repository.github.GitHubIntegration.get_installation_client")
    def test_validate_repository_access_failure(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_repo.side_effect = Exception("Not found")

        result = self.github_integration.validate_repository_access(100, "test-org/test-repo")

        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
