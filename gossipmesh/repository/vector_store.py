from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from gossipmesh.db.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, nullable=False, index=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    branch = Column(String, default="main", nullable=False)
    chunk_index = Column(Integer, default=0, nullable=False)
    filepath = Column(String, nullable=True)
    content = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    metadata_json = Column(JSON, default=dict)


class PGVectorStore:
    def __init__(self, db_session_factory=None):
        self.db_session_factory = db_session_factory

    def search(self, vector: list, filter: dict, top_k: int = 5) -> list:
        return []
