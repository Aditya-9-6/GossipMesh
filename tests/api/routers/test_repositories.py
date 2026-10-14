import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.core.config import settings

client = TestClient(app)

class TestRepositoriesAPI(unittest.TestCase):
    def setUp(self):
        # Create a mock organization with organization_id = 1
        mock_org = MagicMock()
        mock_org.organization_id = 1

        # Create a mock user with the organization
        self.mock_user = MagicMock()
        self.mock_user.organizations = [mock_org]

        # Override dependencies
        self.mock_db = MagicMock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = True

        app.dependency_overrides[deps.get_current_user] = lambda: self.mock_user
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

    def tearDown(self):
        # Clear dependency overrides
        app.dependency_overrides.clear()

    @patch("fastapi.BackgroundTasks.add_task")
    def test_sync_repository_success(self, mock_add_task):
        payload = {
            "full_name": "test/repo",
            "installation_id": 123,
            "organization_id": 1
        }
        response = client.post(f"{settings.API_V1_STR}/repositories/sync", json=payload)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(),
            {"status": "accepted", "message": "Repository sync queued"}
        )
        # Ensure that the background task was queued exactly once
        mock_add_task.assert_called_once()

    @patch("fastapi.BackgroundTasks.add_task")
    def test_sync_repository_unauthorized(self, mock_add_task):
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        payload = {
            "full_name": "test/repo",
            "installation_id": 123,
            "organization_id": 999
        }
        response = client.post(f"{settings.API_V1_STR}/repositories/sync", json=payload)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "AUTHORIZATION_ERROR",
                    "message": "Not authorized for this organization"
                }
            }
        )
        # Ensure that the background task was NOT queued
        mock_add_task.assert_not_called()


    def test_disconnect_repository(self):
        # Mock repo
        mock_repo = MagicMock()
        mock_repo.organization_id = 1
        mock_repo.is_active = True

        # Override for repo query
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_repo, # for getting repo
            True       # for is_admin
        ]

        response = client.patch(f"{settings.API_V1_STR}/repositories/1/disconnect")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Repository disconnected"})
        self.assertFalse(mock_repo.is_active)
        self.mock_db.commit.assert_called_once()

    def test_reconnect_repository(self):
        mock_repo = MagicMock()
        mock_repo.organization_id = 1
        mock_repo.is_active = False

        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_repo,
            True
        ]

        response = client.patch(f"{settings.API_V1_STR}/repositories/1/reconnect")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Repository reconnected"})
        self.assertTrue(mock_repo.is_active)
        self.mock_db.commit.assert_called_once()

    def test_archive_repository(self):
        mock_repo = MagicMock()
        mock_repo.organization_id = 1
        mock_repo.is_active = True
        mock_repo.is_archived = False

        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_repo,
            True
        ]

        response = client.patch(f"{settings.API_V1_STR}/repositories/1/archive")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Repository archived"})
        self.assertTrue(mock_repo.is_archived)
        self.assertFalse(mock_repo.is_active)
        self.mock_db.commit.assert_called_once()

    def test_rename_repository(self):
        mock_repo = MagicMock()
        mock_repo.organization_id = 1

        # side effects: 1) get repo, 2) check is_admin, 3) check existing full_name
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_repo,
            True,
            None # no existing repo
        ]

        payload = {"name": "new-repo", "full_name": "org/new-repo"}
        response = client.patch(f"{settings.API_V1_STR}/repositories/1/rename", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Repository renamed", "name": "new-repo", "full_name": "org/new-repo"})
        self.assertEqual(mock_repo.name, "new-repo")
        self.assertEqual(mock_repo.full_name, "org/new-repo")
        self.mock_db.commit.assert_called_once()

    def test_update_installation(self):
        mock_repo = MagicMock()
        mock_repo.organization_id = 1

        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_repo,
            True
        ]

        payload = {"installation_id": 999}
        response = client.patch(f"{settings.API_V1_STR}/repositories/1/installation", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Installation updated", "installation_id": 999})
        self.assertEqual(mock_repo.installation_id, 999)
        self.mock_db.commit.assert_called_once()

    def test_update_branch(self):
        mock_repo = MagicMock()
        mock_repo.organization_id = 1

        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_repo,
            True
        ]

        payload = {"default_branch": "development"}
        response = client.patch(f"{settings.API_V1_STR}/repositories/1/branch", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "message": "Branch updated", "default_branch": "development"})
        self.assertEqual(mock_repo.default_branch, "development")
        self.mock_db.commit.assert_called_once()

    def test_authorization_fails(self):
        mock_repo = MagicMock()
        mock_repo.organization_id = 1

        # side effects: 1) get repo, 2) check is_admin (False)
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_repo,
            None
        ]

        response = client.patch(f"{settings.API_V1_STR}/repositories/1/disconnect")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": {"code": "AUTHORIZATION_ERROR", "message": "Not authorized for this organization"}})
        self.mock_db.commit.assert_not_called()

if __name__ == "__main__":
    unittest.main()
