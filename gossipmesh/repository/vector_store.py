from typing import Any
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from gossipmesh.models.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Any = Column(String, primary_key=True)
    repo_id: Any = Column(Integer, index=True)
    filepath: Any = Column(String, index=True)
    content: Any = Column(String)
    embedding: Any = Column(Vector(1536))
    metadata_json: Any = Column(JSON)


class PGVectorStore:
    """A minimal abstraction over a pgvector backed SQLAlchemy model."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def upsert(self, id: str, vector: list[float], metadata: dict, content: str = ""):
        chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == id).first()
        if not chunk:
            chunk = DocumentChunk(id=id)
            self.db.add(chunk)

        chunk.repo_id = metadata.get("repo_id")
        chunk.filepath = metadata.get("filepath")
        chunk.embedding = vector
        chunk.metadata_json = metadata
        chunk.content = content

        self.db.commit()

    def search(self, vector: list[float], filter: dict, top_k: int = 5):
        # L2 distance search using pgvector
        stmt = (
            select(DocumentChunk)
            .filter_by(repo_id=filter.get("repo_id"))
            .order_by(DocumentChunk.embedding.l2_distance(vector))
            .limit(top_k)
        )

        results = self.db.execute(stmt).scalars().all()
        return [
            {
                "id": r.id,
                "content": r.content,
                "metadata": r.metadata_json,
                # Note: distance is not returned natively this way without explicit selection
                "score": 0.0,
            }
            for r in results
        ]

    def delete_by_metadata(self, repo_id: int, filepath: str):
        self.db.query(DocumentChunk).filter(
            DocumentChunk.repo_id == repo_id, DocumentChunk.filepath == filepath
        ).delete()
        self.db.commit()
