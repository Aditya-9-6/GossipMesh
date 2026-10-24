""PGVectorStore implementation for semantic code search.""

from typing import Any, Dict, List, Optional

class PGVectorStore:
    def __init__(self, db_session: Any = None):
        self.db_session = db_session

    def delete_by_metadata(self, repo_id: int, filepath: str, organization_id: str, hard_delete: bool = True) -> None:
        pass

    def upsert(self, id: str, vector: List[float], metadata: Dict[str, Any], content: str) -> None:
        pass
