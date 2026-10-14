import unittest

from gossipmesh.auth.authorization import AuthorizationService, Resource, UserContext


class TestAuthorizationService(unittest.TestCase):
    def setUp(self):
        self.auth_service = AuthorizationService()

    def test_allowed_permission(self):
        user = UserContext(user_id="user1", roles={"org1": ["organization_admin"]})
        resource = Resource(id="org1", type="organization")
        self.assertTrue(
            self.auth_service.check_permission(user, resource, "organization:read")
        )
        self.assertTrue(
            self.auth_service.check_permission(user, resource, "billing:write")
        )

    def test_denied_permission(self):
        user = UserContext(user_id="user1", roles={"org1": ["organization_member"]})
        resource = Resource(id="org1", type="organization")
        self.assertFalse(
            self.auth_service.check_permission(user, resource, "organization:write")
        )

    def test_cross_organization(self):
        user = UserContext(user_id="user1", roles={"org1": ["organization_admin"]})
        resource = Resource(id="org2", type="organization")  # Diff org
        self.assertFalse(
            self.auth_service.check_permission(user, resource, "organization:read")
        )

    def test_inactive_user(self):
        user = UserContext(
            user_id="user1", is_active=False, roles={"org1": ["organization_admin"]}
        )
        resource = Resource(id="org1", type="organization")
        self.assertFalse(
            self.auth_service.check_permission(user, resource, "organization:read")
        )

    def test_deleted_resource(self):
        user = UserContext(user_id="user1", roles={"org1": ["organization_admin"]})
        resource = Resource(id="org1", type="organization", is_deleted=True)
        self.assertFalse(
            self.auth_service.check_permission(user, resource, "organization:read")
        )

    def test_service_account(self):
        user = UserContext(user_id="sa1", is_service_account=True)
        resource = Resource(id="org1", type="organization")
        self.assertTrue(
            self.auth_service.check_permission(user, resource, "any:permission")
        )

    def test_project_permissions(self):
        user = UserContext(user_id="user1", roles={"proj1": ["project_admin"]})
        resource = Resource(id="proj1", type="project")
        self.assertTrue(
            self.auth_service.check_permission(user, resource, "project:delete")
        )

    def test_repository_permissions(self):
        user = UserContext(user_id="user1", roles={"repo1": ["repository_admin"]})
        resource = Resource(id="repo1", type="repository")
        self.assertTrue(
            self.auth_service.check_permission(user, resource, "approval:write")
        )


if __name__ == "__main__":
    unittest.main()
