import time
import jwt
from github import Github, Auth

class GitHubIntegration:
    def __init__(self, app_id: str, private_key: str):
        self.app_id = app_id
        self.private_key = private_key
        self.app_auth = Auth.AppAuth(self.app_id, self.private_key)

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
        # In a real app we'd fetch the installation access token from the API
        # Using PyGithub's built-in AppAuth with instance caching
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

    def generate_installation_token(self, installation_id: int):
        """Generates an installation token with expiration."""
        # Using PyGithub's AppAuth for installation authentication natively handles tokens
        # and caching across multiple calls since it is persisted on the class instance.
        installation_auth = self.app_auth.get_installation_auth(installation_id)
        # By calling token property, PyGithub will automatically create one or return cached
        token_str = installation_auth.token
        return token_str

    def validate_repository_access(self, installation_id: int, repository_name: str) -> bool:
        """Validates that the installation has access to a specific repository."""
        try:
            client = self.get_installation_client(installation_id)
            repo = client.get_repo(repository_name)
            return repo.name is not None
        except Exception:
            return False
