import unittest
from unittest.mock import patch, MagicMock
from gossipmesh.repository.github import GitHubIntegration

class TestGitHubIntegration(unittest.TestCase):
    @patch('gossipmesh.repository.github.Auth.AppAuth')
    @patch('gossipmesh.repository.github.Github')
    def test_get_app_client_success(self, mock_github, mock_app_auth):
        mock_auth_instance = MagicMock()
        mock_app_auth.return_value = mock_auth_instance

        integration = GitHubIntegration(app_id="123", private_key="mock_key")
        client = integration.get_app_client()

        mock_app_auth.assert_called_once_with("123", "mock_key")
        mock_github.assert_called_once_with(auth=mock_auth_instance)
        self.assertEqual(client, mock_github.return_value)

    @patch('gossipmesh.repository.github.Auth.AppAuth')
    @patch('gossipmesh.repository.github.Github')
    def test_get_installation_client_success(self, mock_github, mock_app_auth):
        mock_auth_instance = MagicMock()
        mock_app_auth.return_value = mock_auth_instance

        mock_installation_auth = MagicMock()
        mock_auth_instance.get_installation_auth.return_value = mock_installation_auth

        integration = GitHubIntegration(app_id="123", private_key="mock_key")
        client = integration.get_installation_client(456)

        mock_auth_instance.get_installation_auth.assert_called_once_with(456)
        mock_github.assert_called_once_with(auth=mock_installation_auth)
        self.assertEqual(client, mock_github.return_value)

if __name__ == '__main__':
    unittest.main()
