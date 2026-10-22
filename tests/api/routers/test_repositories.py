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
        payload = {"full_name": "test/repo", "installation_id": 123, "organization_id": 1}
        response = client.post(f"{settings.API_V1_STR}/repositories/sync", json=payload)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"status": "accepted", "message": "Repository sync queued"})
        # Ensure that the background task was queued exactly once
        mock_add_task.assert_called_once()

    @patch("fastapi.BackgroundTasks.add_task")
    def test_sync_repository_unauthorized(self, mock_add_task):
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        payload = {"full_name": "test/repo", "installation_id": 123, "organization_id": 999}
        response = client.post(f"{settings.API_V1_STR}/repositories/sync", json=payload)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {"error": {"code": "AUTHORIZATION_ERROR", "message": "Not authorized for this organization"}},
        )
        # Ensure that the background task was NOT queued
        mock_add_task.assert_not_called()

    def test_update_repository_success(self):
        # Mock repository exists and user is admin
        mock_repo = MagicMock()
        mock_repo.id = 1
        mock_repo.organization_id = 1
        mock_repo.full_name = "test/repo"
        mock_repo.default_branch = "main"
        mock_repo.policy = None

        self.mock_user.id = 1

        # We need first call (repo lookup) to return repo, second call (admin check) to return user_org
        def mock_first():
            class MockQuery:
                def __init__(self, is_repo=False):
                    self.is_repo = is_repo

                def filter(self, *args, **kwargs):
                    return self

                def first(self):
                    if self.is_repo:
                        return mock_repo
                    return True  # mock user_org for admin check

            return MockQuery()

        def side_effect(*args, **kwargs):
            from gossipmesh.models.repository import Repository

            is_repo = args[0] == Repository if args else False

            class MockQuery:
                def filter(self, *filter_args, **filter_kwargs):
                    class FilteredMockQuery:
                        def first(self):
                            if is_repo:
                                return mock_repo
                            return True  # admin check passes

                    return FilteredMockQuery()

            return MockQuery()

        self.mock_db.query.side_effect = side_effect

        payload = {"default_branch": "develop", "policy": {"require_approval": True}}
        response = client.patch(f"{settings.API_V1_STR}/repositories/1", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_repo.default_branch, "develop")
        self.assertEqual(mock_repo.policy, {"require_approval": True})

        # Verify db.add was called for AuditEvent
        self.mock_db.add.assert_called()
        self.mock_db.commit.assert_called()

    def test_update_repository_not_found(self):
        def side_effect(*args, **kwargs):
            from gossipmesh.models.repository import Repository

            is_repo = args[0] == Repository if args else False

            class MockQuery:
                def filter(self, *filter_args, **filter_kwargs):
                    class FilteredMockQuery:
                        def first(self):
                            if is_repo:
                                return None
                            return True

                    return FilteredMockQuery()

            return MockQuery()

        self.mock_db.query.side_effect = side_effect

        payload = {"default_branch": "develop"}
        response = client.patch(f"{settings.API_V1_STR}/repositories/999", json=payload)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Repository not found")

    def test_delete_repository_success(self):
        # We need a proper Repository model instance (or a Mock with __tablename__ and class hierarchy)
        # so that SQLAlchemy's delete logic doesn't fail in some configurations.
        from gossipmesh.models.repository import Repository

        mock_repo = MagicMock(spec=Repository)
        mock_repo.id = 1
        mock_repo.organization_id = 1
        mock_repo.full_name = "test/repo"
        mock_repo.__tablename__ = "repositories"

        self.mock_user.id = 1

        def side_effect(*args, **kwargs):
            from gossipmesh.models.repository import Repository

            is_repo = args[0] == Repository if args else False

            class MockQuery:
                def filter(self, *filter_args, **filter_kwargs):
                    class FilteredMockQuery:
                        def first(self):
                            if is_repo:
                                return mock_repo
                            return True  # admin check passes

                    return FilteredMockQuery()

            return MockQuery()

        self.mock_db.query.side_effect = side_effect

        response = client.delete(f"{settings.API_V1_STR}/repositories/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Repository removed"})
        self.mock_db.delete.assert_called_with(mock_repo)
        self.mock_db.commit.assert_called()

    def test_delete_repository_unauthorized(self):
        mock_repo = MagicMock()
        mock_repo.id = 1
        mock_repo.organization_id = 1
        mock_repo.full_name = "test/repo"

        def side_effect(*args, **kwargs):
            from gossipmesh.models.repository import Repository

            is_repo = args[0] == Repository if args else False

            class MockQuery:
                def filter(self, *filter_args, **filter_kwargs):
                    class FilteredMockQuery:
                        def first(self):
                            if is_repo:
                                return mock_repo
                            return None  # admin check fails

                    return FilteredMockQuery()

            return MockQuery()

        self.mock_db.query.side_effect = side_effect

        response = client.delete(f"{settings.API_V1_STR}/repositories/1")

        self.assertEqual(response.status_code, 403)
        self.mock_db.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
