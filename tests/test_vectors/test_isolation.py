import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from gossipmesh.api.main import app
from gossipmesh.api import deps
from gossipmesh.core.config import settings
from gossipmesh.core.exceptions import AuthorizationError

class TestOrganizationScoping(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Mock users for org A and org B
        self.mock_user_a = MagicMock()
        self.mock_user_a.id = 1
        mock_org_a = MagicMock()
        mock_org_a.organization_id = 1
        self.mock_user_a.organizations = [mock_org_a]

        self.mock_user_b = MagicMock()
        self.mock_user_b.id = 2
        mock_org_b = MagicMock()
        mock_org_b.organization_id = 2
        self.mock_user_b.organizations = [mock_org_b]

        # Mock db
        self.mock_db = MagicMock()

        # Override dependencies
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_cross_tenant_record_access_prevented(self):
        app.dependency_overrides[deps.get_current_user] = lambda: self.mock_user_a

        # Try to access a workflow belonging to Org B
        workflow_mock = MagicMock()
        workflow_mock.organization_id = 2

        # We simulate the db.query for Workflow returning workflow_mock, but db.query for UserOrganization returning None
        def mock_query(model):
            mock_query_obj = MagicMock()
            if model.__name__ == 'Workflow':
                mock_query_obj.filter.return_value.first.return_value = workflow_mock
            elif model.__name__ == 'UserOrganization':
                mock_query_obj.filter.return_value.first.return_value = None
            return mock_query_obj

        self.mock_db.query.side_effect = mock_query

        # When User A tries to cancel workflow 99 (which belongs to Org B)
        response = self.client.post(f"{settings.API_V1_STR}/runtime/workflows/99/cancel", headers={"Authorization": "Bearer mocked_token"})
        self.assertEqual(response.status_code, 403)

        # Check that the error message contains 'Not authorized' (using our custom exception handler format)
        resp_json = response.json()
        self.assertIn("Not authorized", resp_json["error"]["message"])

    def test_cross_tenant_artifact_access_prevented(self):
        # Setup mock db query
        artifact_mock = MagicMock()
        artifact_mock.job.workflow.organization_id = 2

        def mock_query(model):
            mock_query_obj = MagicMock()
            if model.__name__ == 'Artifact':
                mock_query_obj.join.return_value.join.return_value.filter.return_value.first.return_value = artifact_mock
            elif model.__name__ == 'UserOrganization':
                mock_query_obj.filter.return_value.first.return_value = None
            return mock_query_obj

        self.mock_db.query.side_effect = mock_query

        # App dependency overrides
        app.dependency_overrides[deps.get_current_user] = lambda: self.mock_user_a
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

        # When User A tries to access Artifact 1 (which belongs to Org B)
        response = self.client.get(f"{settings.API_V1_STR}/artifacts/1", headers={"Authorization": "Bearer mocked_token"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Not authorized to access this artifact", response.json()["error"]["message"])

    def test_cross_tenant_audit_log_access_prevented(self):
        # We simulate the filter for UserOrganization returning None
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[deps.get_current_user] = lambda: self.mock_user_a
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

        # When User A tries to access logs for tenant 2 (which belongs to Org B)
        response = self.client.get(f"{settings.API_V1_STR}/enterprise/audit-logs/2", headers={"Authorization": "Bearer mocked_token"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Not authorized for this organization", response.json()["error"]["message"])

    def test_cross_tenant_vector_search_prevented(self):
        # Setup mock db query
        repo_mock = MagicMock()
        repo_mock.organization_id = 2

        def mock_query(model):
            mock_query_obj = MagicMock()
            if model.__name__ == 'Repository':
                mock_query_obj.filter.return_value.first.return_value = repo_mock
            elif model.__name__ == 'UserOrganization':
                mock_query_obj.filter.return_value.first.return_value = None
            return mock_query_obj

        self.mock_db.query.side_effect = mock_query

        # App dependency overrides
        app.dependency_overrides[deps.get_current_user] = lambda: self.mock_user_a
        app.dependency_overrides[deps.get_db] = lambda: self.mock_db

        payload = {"query": "test query", "repo_id": 1, "top_k": 5}
        # When User A tries to search vectors for Repository 1 (which belongs to Org B)
        response = self.client.post(f"{settings.API_V1_STR}/vector_search/search", json=payload, headers={"Authorization": "Bearer mocked_token"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Not authorized for this organization", response.json()["error"]["message"])

if __name__ == '__main__':
    unittest.main()
