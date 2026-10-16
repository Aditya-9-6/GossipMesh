import time
import jwt
from github import Github, Auth
from github.Installation import Installation
from gossipmesh.core.config import settings

class GitHubIntegration:
    def __init__(self, app_id: str | None = None, private_key: str | None = None):
        self.app_id = app_id or settings.GITHUB_APP_ID
        self.private_key = private_key or settings.GITHUB_APP_PRIVATE_KEY
        if not self.app_id or not self.private_key:
            raise ValueError("GitHub App ID and private key must be provided or configured in settings.")

        self.app_auth = Auth.AppAuth(self.app_id, self.private_key)

    def get_app_client(self) -> Github:
        """Returns a Github client authenticated as the App."""
        return Github(auth=self.app_auth)

    def get_installation_client(self, installation_id: int) -> Github:
        """Returns a Github client authenticated as a specific installation."""
        auth = self.app_auth.get_installation_auth(installation_id)
        return Github(auth=auth)

    def sync_repository(self, full_name: str, installation_id: int):
        """Mock method for synchronizing repository metadata."""
        client = self.get_installation_client(installation_id)
        repo = client.get_repo(full_name)
        # We would typically save repo.id, repo.default_branch, etc. to our database
        return {
            "github_id": repo.id,
            "name": repo.name,
            "default_branch": repo.default_branch,
            "clone_url": repo.clone_url
        }
