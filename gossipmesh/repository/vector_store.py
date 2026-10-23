"""Production Vector Storage with pgvector and Multi-Tenant Isolation (Task 75).

Stores and indexes code embeddings with comprehensive enterprise metadata:
organization, repository, branch, file, chunk index, SHA-256 chunk hash,
embedding provider, embedding version, soft deletion, and retention expiration.
"""

from datetime import datetime, timezone
import hashlib
import math
from typing import Any, Dict, List, Optional
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from gossipmesh.models.base import Base


class DocumentChunk(Base):
    """Production vector chunk model backed by PostgreSQL pgvector."""

    __tablename__ = "document_chunks"

    id: Any = Column(String(256), primary_key=True)
    organization_id: Any = Column(String(128), index=True, nullable=False, default="default")
    repo_id: Any = Column(Integer, index=True, nullable=True)
    repository_id: Any = Column(Integer, index=True, nullable=True)
    branch: Any = Column(String(256), index=True, default="main")
    filepath: Any = Column(String(1024), index=True, nullable=True)
    chunk_index: Any = Column(Integer, default=0)
    chunk_hash: Any = Column(String(64), index=True, nullable=True)
    content: Any = Column(Text, nullable=False, default="")
    embedding: Any = Column(Vector(1536), nullable=True)
    provider: Any = Column(String(128), default="openai:text-embedding-3-small")
    embedding_version: Any = Column(String(32), default="v1")
    is_deleted: Any = Column(Boolean, default=False, index=True)
    retention_expires_at: Any = Column(DateTime(timezone=True), nullable=True)
    metadata_json: Any = Column(JSON, default=dict)
    created_at: Any = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Any = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PGVectorStore:
    """Production vector storage engine with tenant isolation and retention lifecycle."""

    def __init__(self, db_session: Session):
        self.db = db_session

    @staticmethod
    def compute_chunk_hash(content: str) -> str:
        """Computes SHA-256 hash of chunk content for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def upsert(
        self,
        id: str,
        vector: list[float],
        metadata: dict,
        content: str = "",
    ) -> DocumentChunk:
        """Upserts a document chunk with full enterprise metadata."""
        chunk = self.db.query(DocumentChunk).filter(DocumentChunk.id == id).first()
        if not chunk:
            chunk = DocumentChunk(id=id)
            self.db.add(chunk)

        # Organization & Repository scoping
        org_id = str(metadata.get("organization_id") or metadata.get("org_id") or "default")
        repo_val = metadata.get("repository_id") or metadata.get("repo_id")
        repo_id_int = int(repo_val) if repo_val is not None else None

        chunk.organization_id = org_id
        chunk.repo_id = repo_id_int
        chunk.repository_id = repo_id_int
        chunk.branch = str(metadata.get("branch") or "main")
        chunk.filepath = metadata.get("filepath") or metadata.get("file_path")
        chunk.chunk_index = int(metadata.get("chunk_index") or 0)
        chunk.content = content

        # SHA-256 chunk content hash
        chunk.chunk_hash = metadata.get("chunk_hash") or self.compute_chunk_hash(content)

        # Provider & Version tracking
        chunk.provider = str(metadata.get("provider") or "openai:text-embedding-3-small")
        chunk.embedding_version = str(metadata.get("embedding_version") or "v1")

        # Lifecycle & Retention
        chunk.is_deleted = bool(metadata.get("is_deleted", False))
        chunk.retention_expires_at = metadata.get("retention_expires_at")

        chunk.embedding = vector

        # Ensure metadata_json contains only JSON-serializable objects (e.g. stringify datetimes)
        clean_metadata = {}
        for k, v in metadata.items():
            if isinstance(v, datetime):
                clean_metadata[k] = v.isoformat()
            else:
                clean_metadata[k] = v
        chunk.metadata_json = clean_metadata

        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def search(
        self,
        vector: list[float],
        filter: dict,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Searches top-k similar vectors scoped by tenant organization, repository, and branch.
        Filters out soft-deleted and retention-expired chunks.
        """
        query = self.db.query(DocumentChunk)

        # 1. Tenant & Repository Filtering
        if "organization_id" in filter:
            query = query.filter(DocumentChunk.organization_id == str(filter["organization_id"]))

        repo_val = filter.get("repo_id") or filter.get("repository_id")
        if repo_val is not None:
            query = query.filter(
                (DocumentChunk.repo_id == int(repo_val)) | (DocumentChunk.repository_id == int(repo_val))
            )

        if "branch" in filter:
            query = query.filter(DocumentChunk.branch == str(filter["branch"]))

        if "filepath" in filter:
            query = query.filter(DocumentChunk.filepath == str(filter["filepath"]))

        # 2. Exclude soft-deleted chunks
        query = query.filter(DocumentChunk.is_deleted.is_(False))

        # 3. Exclude retention-expired chunks
        now = datetime.now(timezone.utc)
        query = query.filter(
            (DocumentChunk.retention_expires_at.is_(None)) | (DocumentChunk.retention_expires_at > now)
        )

        # Check if executing against SQLite (test mode) or PostgreSQL (production pgvector)
        is_sqlite = False
        try:
            bind = getattr(self.db, "bind", None) or self.db.get_bind()
            if bind and bind.dialect.name == "sqlite":
                is_sqlite = True
        except Exception:
            pass

        if is_sqlite:
            # Fallback Python Euclidean L2 distance for SQLite test harness
            candidates = query.all()
            scored_candidates = []
            for r in candidates:
                if r.embedding is not None and len(r.embedding) == len(vector):
                    dist = math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(r.embedding, vector)))
                    similarity_score = 1.0 / (1.0 + dist)
                else:
                    dist = float("inf")
                    similarity_score = 0.0
                scored_candidates.append((dist, similarity_score, r))

            scored_candidates.sort(key=lambda x: x[0])
            top_results = scored_candidates[:top_k]

            return [
                {
                    "id": r.id,
                    "content": r.content,
                    "metadata": r.metadata_json,
                    "score": round(score, 4),
                    "organization_id": r.organization_id,
                    "repository_id": r.repository_id,
                    "filepath": r.filepath,
                    "chunk_index": r.chunk_index,
                    "provider": r.provider,
                }
                for _, score, r in top_results
            ]
        else:
            # Native PostgreSQL pgvector L2 search
            stmt = query.order_by(DocumentChunk.embedding.l2_distance(vector)).limit(top_k)
            results = stmt.all()
            return [
                {
                    "id": r.id,
                    "content": r.content,
                    "metadata": r.metadata_json,
                    "score": 0.0,
                    "organization_id": r.organization_id,
                    "repository_id": r.repository_id,
                    "filepath": r.filepath,
                    "chunk_index": r.chunk_index,
                    "provider": r.provider,
                }
                for r in results
            ]

    def soft_delete(self, id: str, organization_id: Optional[str] = None) -> bool:
        """Soft-deletes a chunk by setting is_deleted=True."""
        query = self.db.query(DocumentChunk).filter(DocumentChunk.id == id)
        if organization_id:
            query = query.filter(DocumentChunk.organization_id == organization_id)
        chunk = query.first()
        if chunk:
            chunk.is_deleted = True
            self.db.commit()
            return True
        return False

    def delete_by_metadata(
        self,
        repo_id: int,
        filepath: str,
        organization_id: Optional[str] = None,
        hard_delete: bool = False,
    ) -> int:
        """Deletes chunks matching repo_id and filepath (soft by default, or hard)."""
        query = self.db.query(DocumentChunk).filter(
            (DocumentChunk.repo_id == repo_id) | (DocumentChunk.repository_id == repo_id),
            DocumentChunk.filepath == filepath,
        )
        if organization_id:
            query = query.filter(DocumentChunk.organization_id == organization_id)

        if hard_delete:
            count = query.delete(synchronize_session=False)
            self.db.commit()
            return count
        else:
            chunks = query.all()
            for c in chunks:
                c.is_deleted = True
            self.db.commit()
            return len(chunks)

    def purge_expired(self, organization_id: Optional[str] = None) -> int:
        """Purges chunks whose retention has expired."""
        now = datetime.now(timezone.utc)
        query = self.db.query(DocumentChunk).filter(
            DocumentChunk.retention_expires_at.isnot(None),
            DocumentChunk.retention_expires_at <= now,
        )
        if organization_id:
            query = query.filter(DocumentChunk.organization_id == organization_id)

        count = query.delete(synchronize_session=False)
        self.db.commit()
        return count
