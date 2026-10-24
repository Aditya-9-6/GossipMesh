from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.organization import Organization
from gossipmesh.models.repository import Repository
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.repository.retrieval import HybridRetriever
from gossipmesh.repository.vector_store import PGVectorStore

router = APIRouter()


class VectorSearchRouterHelper:
    def check_repo(self, repo: Repository) -> Dict[str, Any]:
        repo_id = getattr(repo, "id", None)
        org_id = getattr(repo, "organization_id", None)
        return {"repository_id": repo_id, "organization_id": org_id}


class SearchQuery(BaseModel):
    query: str
    repo_id: int
    top_k: int = 5


@router.post("/search")
def search_vectors(
    search_query: SearchQuery, current_user: User = Depends(deps.get_current_user), db: Session = Depends(deps.get_db)
) -> Any:
    # Look up the repository to find its organization
    repo = db.query(Repository).filter(Repository.id == search_query.repo_id).first()
    if not repo:
        raise AuthorizationError(message="Repository not found")

    # Check if the user belongs to the repository's organization
    is_member = (
        db.query(UserOrganization)
        .filter(UserOrganization.user_id == current_user.id, UserOrganization.organization_id == repo.organization_id)
        .first()
    )
    if not is_member:
        raise AuthorizationError(message="Not authorized for this organization")

    # Proceed with search safely
    store = PGVectorStore(db)

    # Dummy graph for the prototype
    class DummyGraph:
        def get_dependencies(self, filepath):
            return []

    retriever = HybridRetriever(store, DummyGraph())
    results = retriever.search(search_query.query, search_query.repo_id, search_query.top_k)
    return {"results": results}
