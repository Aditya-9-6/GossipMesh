import tests # apply global patches
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.core.config import settings
from gossipmesh.models.jobs import BackgroundJob

client = TestClient(app)

class TestJobsAPI(unittest.TestCase):
    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.is_superuser = False

        self.mock_db = MagicMock()

        app.dependency_overrides[deps.get_current_user] = lambda: self.mock_user
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_job_status_success(self):
        mock_job = BackgroundJob(task_id="123", task_name="test_task", user_id=1, status="success", result={"key": "val"})
        def mock_query(model):
            mock_query_obj = MagicMock()
            if model.__name__ == 'BackgroundJob':
                mock_query_obj.filter.return_value.first.return_value = mock_job
            elif model.__name__ == 'UserOrganization':
                mock_query_obj.filter.return_value.first.return_value = None
            return mock_query_obj
        self.mock_db.query.side_effect = mock_query

        response = client.get(f"{settings.API_V1_STR}/jobs/123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["result"], {"key": "val"})

    def test_get_job_status_unauthorized(self):
        mock_job = BackgroundJob(task_id="123", task_name="test_task", user_id=99, status="success")
        def mock_query(model):
            mock_query_obj = MagicMock()
            if model.__name__ == 'BackgroundJob':
                mock_query_obj.filter.return_value.first.return_value = mock_job
            elif model.__name__ == 'UserOrganization':
                mock_query_obj.filter.return_value.first.return_value = None
            return mock_query_obj
        self.mock_db.query.side_effect = mock_query

        response = client.get(f"{settings.API_V1_STR}/jobs/123")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["message"], "Not authorized to access this job")

    @patch("gossipmesh.api.routers.jobs.celery_app.control.revoke")
    def test_cancel_job_success(self, mock_revoke):
        mock_job = BackgroundJob(task_id="123", task_name="test_task", user_id=1, status="running")
        def mock_query(model):
            mock_query_obj = MagicMock()
            if model.__name__ == 'BackgroundJob':
                mock_query_obj.filter.return_value.first.return_value = mock_job
            elif model.__name__ == 'UserOrganization':
                mock_query_obj.filter.return_value.first.return_value = None
            return mock_query_obj
        self.mock_db.query.side_effect = mock_query

        response = client.post(f"{settings.API_V1_STR}/jobs/123/cancel")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "cancelled")
        mock_revoke.assert_called_once_with("123", terminate=True)
        self.assertEqual(mock_job.status, "cancelled")

    def test_cancel_job_completed_error(self):
        mock_job = BackgroundJob(task_id="123", task_name="test_task", user_id=1, status="success")
        def mock_query(model):
            mock_query_obj = MagicMock()
            if model.__name__ == 'BackgroundJob':
                mock_query_obj.filter.return_value.first.return_value = mock_job
            elif model.__name__ == 'UserOrganization':
                mock_query_obj.filter.return_value.first.return_value = None
            return mock_query_obj
        self.mock_db.query.side_effect = mock_query

        response = client.post(f"{settings.API_V1_STR}/jobs/123/cancel")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Cannot cancel a completed job")

if __name__ == "__main__":
    unittest.main()
