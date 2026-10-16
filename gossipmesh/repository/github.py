import time
import jwt
from typing import Dict, Optional
from github import Github, Auth
from github.Installation import Installation
from gossipmesh.core.config import settings
from gossipmesh.core.exceptions import AuthorizationError

class GitHubIntegration:
    def __init__(self, app_id: str, private_key: str, permissions: Optional[Dict[str, str]] = None):
        self.app_id = app_id
        self.private_key = private_key
        self.permissions = permissions

    def _check_permissions(self, required_permissions: Dict[str, str]) -> None:
        """
        Validates that the provided permissions dictionary contains the required scopes.
        Raises AuthorizationError if the check fails.
        If self.permissions is None, the check is skipped.
        """
        if self.permissions is None:
            return

        for scope, required_level in required_permissions.items():
            granted_level = self.permissions.get(scope)
            if not granted_level:
                raise AuthorizationError(
                    f"Missing required permission scope: '{scope}'",
                    details={"required": required_permissions, "granted": self.permissions}
                )

            # If required is read, granted can be read or write
            if required_level == "read" and granted_level not in ("read", "write"):
                raise AuthorizationError(
                    f"Insufficient permission for '{scope}'. Required: {required_level}, Granted: {granted_level}",
                    details={"required": required_permissions, "granted": self.permissions}
                )
            # If required is write, granted must be write
            elif required_level == "write" and granted_level != "write":
                raise AuthorizationError(
                    f"Insufficient permission for '{scope}'. Required: {required_level}, Granted: {granted_level}",
                    details={"required": required_permissions, "granted": self.permissions}
                )

    def _generate_jwt(self) -> str:
        payload = {
            "iat": int(time.time()) - 60,
            "exp": int(time.time()) + (10 * 60),
            "iss": self.app_id
        }
        encoded = jwt.encode(payload, self.private_key, algorithm="RS256")
        return encoded if isinstance(encoded, str) else encoded.decode("utf-8")

    def get_app_client(self) -> Github:
        """Returns a Github client authenticated as the App."""
        token = self._generate_jwt()
        auth = Auth.Token(token)
        return Github(auth=auth)

    def get_installation_client(self, installation_id: int) -> Github:
        """Returns a Github client authenticated as a specific installation."""
        self.get_app_client()
        # In a real app we'd fetch the installation access token from the API
        # Using PyGithub's built-in AppAuth
        auth = Auth.AppAuth(
            self.app_id,
            self.private_key,
        ).get_installation_auth(installation_id)
        return Github(auth=auth)

    def sync_repository(self, full_name: str, installation_id: int):
        """Mock method for synchronizing repository metadata."""
        self._check_permissions({"metadata": "read"})
        client = self.get_installation_client(installation_id)
        repo = client.get_repo(full_name)
        # We would typically save repo.id, repo.default_branch, etc. to our database
        return {
            "github_id": repo.id,
            "name": repo.name,
            "default_branch": repo.default_branch,
            "clone_url": repo.clone_url
        }
