from typing import Dict, List, Optional
from pydantic import BaseModel


class Resource(BaseModel):
    id: str
    type: str  # organization, project, repository, billing, audit, approval
    is_deleted: bool = False


class UserContext(BaseModel):
    user_id: str
    is_active: bool = True
    is_service_account: bool = False
    roles: Dict[str, List[str]] = {}  # resource_id -> list of roles (e.g. admin, member)


class AuthorizationService:
    def __init__(self):
        # We need a centralized service to check permissions.

        # Roles and their allowed permissions mapping
        self.role_permissions: Dict[str, List[str]] = {
            "organization_admin": [
                "organization:read",
                "organization:write",
                "organization:delete",
                "billing:read",
                "billing:write",
                "audit:read",
            ],
            "organization_member": ["organization:read"],
            "project_admin": ["project:read", "project:write", "project:delete"],
            "project_member": ["project:read"],
            "repository_admin": ["repository:read", "repository:write", "repository:delete", "approval:write"],
            "repository_member": ["repository:read"],
            "service_account": ["*"],  # example for service accounts
        }

    def _get_permissions_for_role(self, role: str) -> List[str]:
        return self.role_permissions.get(role, [])

    def check_permission(self, user: UserContext, resource: Resource, permission: str) -> bool:
        """
        Check if the user has the required permission on the resource.
        """
        if not user.is_active:
            return False

        if resource.is_deleted:
            return False

        if user.is_service_account:
            # Service accounts might bypass some checks or have specific roles
            roles = user.roles.get(resource.id, ["service_account"])
        else:
            roles = user.roles.get(resource.id, [])

        for role in roles:
            allowed_permissions = self._get_permissions_for_role(role)
            if "*" in allowed_permissions:
                return True
            if permission in allowed_permissions:
                return True

        return False
