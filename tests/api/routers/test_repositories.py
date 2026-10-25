import sys
from unittest.mock import MagicMock, patch

if "psycopg2" not in sys.modules:
    sys.modules["psycopg2"] = MagicMock()

import unittest
from fastapi.testclient import TestClient
from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.core.config import settings

client = TestClient(app)


class TestRepositoriesAPI(unittest.TestCase):
    def setUp(self):
        mock_org = MagicMock()
        mock_org.organization_id = 1
        self.mock_user = MagicMock()
        self.mock_user.is_superuser = False
        self.mock_user.organizations = [mock_org]
        self.mock_db = MagicMock()
        self.mock_db.query.return_value.filter.return_value.first.return_value = True
        app.dependency_overrides[deps.get_current_user] = lambda: self.mock_user
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("fastapi.BackgroundTasks.add_task")
    def test_sync_repository_success(self, mock_add_task):
        payload = {"full_name": "test/repo", "installation_id": 123, "organization_id": 1}
        response = client.post(f"{settings.API_V1_STR}/repositories/sync", json=payload)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"status": "accepted", "message": "Repository sync queued"})
        mock_add_task.assert_called_once()

    @patch("fastapi.BackgroundTasks.add_task")
    def test_sync_repository_unauthorized(self, mock_add_task):
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        payload = {"full_name": "test/repo", "installation_id": 123, "organization_id": 999}
        response = client.post(f"{settings.API_V1_STR}/repositories/sync", json=payload)
        self.assertEqual(response.status_code, 403)
        mock_add_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
