from typing import Any, Dict
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository


class VectorSearchRouterHelper:
    def check_repo(self, repo: Repository) -> Dict[str, Any]:
        repo_id = getattr(repo, "id", None)
        org_id = getattr(repo, "organization_id", None)
        return {"repository_id": repo_id, "organization_id": org_id}
