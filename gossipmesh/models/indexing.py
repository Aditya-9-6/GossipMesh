"""SQLAlchemy Models for Incremental Indexing Jobs and File Tracking (Task 76)."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func
from gossipmesh.models.base import Base


class IndexJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class IndexJob(Base):
    """Tracks status, progress, versioning, and metrics of an indexing job."""

    __tablename__ = "index_jobs"

    id = Column(String(64), primary_key=True)
    organization_id = Column(String(128), index=True, nullable=False)
    repository_id = Column(Integer, index=True, nullable=False)
    branch = Column(String(256), default="main", nullable=False)
    commit_sha = Column(String(64), nullable=False)

    status = Column(String(32), default=IndexJobStatus.PENDING.value, index=True, nullable=False)
    progress_pct = Column(Float, default=0.0, nullable=False)
    total_files = Column(Integer, default=0, nullable=False)
    files_processed = Column(Integer, default=0, nullable=False)
    files_indexed = Column(Integer, default=0, nullable=False)
    files_skipped = Column(Integer, default=0, nullable=False)
    files_deleted = Column(Integer, default=0, nullable=False)
    chunks_created = Column(Integer, default=0, nullable=False)

    job_version = Column(String(32), default="v1", nullable=False)
    is_cancelled = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "repository_id": self.repository_id,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "status": self.status,
            "progress_pct": round(self.progress_pct, 2),
            "total_files": self.total_files,
            "files_processed": self.files_processed,
            "files_indexed": self.files_indexed,
            "files_skipped": self.files_skipped,
            "files_deleted": self.files_deleted,
            "chunks_created": self.chunks_created,
            "job_version": self.job_version,
            "is_cancelled": self.is_cancelled,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FileIndexRecord(Base):
    """Tracks per-file content hash and commit SHA to power incremental change detection."""

    __tablename__ = "file_index_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(String(128), index=True, nullable=False)
    repository_id = Column(Integer, index=True, nullable=False)
    filepath = Column(String(1024), index=True, nullable=False)
    file_hash = Column(String(64), index=True, nullable=False)
    commit_sha = Column(String(64), nullable=False)
    last_indexed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
