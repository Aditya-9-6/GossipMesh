from typing import Any, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.repository.retrieval import PermissionAwareRetriever
from gossipmesh.repository.vector_store import PGVectorStore

router = APIRouter()


class SearchQuery(BaseModel):
    query: str
    repo_id: int
    branch: Optional[str] = "main"
    top_k: int = 5


@router.post("/search")
def search_vectors(
    search_query: SearchQuery,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """Performs permission-aware vector search strictly isolating tenant data."""
    store = PGVectorStore(db)

    # Dummy graph for the prototype
    class DummyGraph:
        def get_dependencies(self, filepath):
            return []

    retriever = PermissionAwareRetriever(store, DummyGraph())
    results = retriever.search(
        query=search_query.query,
        repo_id=search_query.repo_id,
        user=current_user,
        db=db,
        branch=search_query.branch or "main",
        top_k=search_query.top_k,
    )
    return {"results": results}
