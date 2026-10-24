"""Incremental Repository Indexing Engine (Task 76)."""

from datetime import datetime, timezone
import hashlib
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional
import uuid
from sqlalchemy.orm import Session

from gossipmesh.models.indexing import FileIndexRecord, IndexJob, IndexJobStatus
from gossipmesh.repository.chunking import chunk_python_code
from gossipmesh.repository.vector_store import PGVectorStore

logger = logging.getLogger(__name__)


class FileChange:
    def __init__(self, path: str, content: str = "", status: str = "modified"):
        self.path = path
        self.content = content
        self.status = status.lower()


class IncrementalIndexer:
    def __init__(
        self,
        vector_store: PGVectorStore,
        db_session: Session,
        embedding_model=None,
    ):
        self.vector_store = vector_store
        self.db = db_session
        self.embedding_model = embedding_model

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def create_index_job(
        self,
        organization_id: str,
        repository_id: int,
        commit_sha: str,
        branch: str = "main",
        job_version: str = "v1",
    ) -> IndexJob:
        job_id = f"idx-{uuid.uuid4().hex[:16]}"
        job = IndexJob(
            id=job_id,
            organization_id=organization_id,
            repository_id=repository_id,
            branch=branch,
            commit_sha=commit_sha,
            status=IndexJobStatus.PENDING.value,
            progress_pct=0.0,
            job_version=job_version,
            is_cancelled=False,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def cancel_job(self, job_id: str) -> bool:
        job = self.db.query(IndexJob).filter(IndexJob.id == job_id).first()
        if job and job.status in (IndexJobStatus.PENDING.value, IndexJobStatus.RUNNING.value):
            job.is_cancelled = True
            job.status = IndexJobStatus.CANCELLED.value
            self.db.commit()
            return True
        return False

    def is_cancelled(self, job_id: str) -> bool:
        job = self.db.query(IndexJob).filter(IndexJob.id == job_id).first()
        return bool(job and (job.is_cancelled or job.status == IndexJobStatus.CANCELLED.value))

    def sync_repository(
        self,
        job_id: str,
        file_changes: List[FileChange],
        progress_callback: Optional[Callable[[int, int, float, str], None]] = None,
    ) -> IndexJob:
        job = self.db.query(IndexJob).filter(IndexJob.id == job_id).first()
        if not job:
            raise ValueError(f"Index job {job_id} not found")

        job.status = IndexJobStatus.RUNNING.value
        job.total_files = len(file_changes)
        job.files_processed = 0
        self.db.commit()

        org_id = job.organization_id
        repo_id = job.repository_id
        branch = job.branch
        commit_sha = job.commit_sha
        job_version = job.job_version

        try:
            for idx, change in enumerate(file_changes, start=1):
                if self.is_cancelled(job_id):
                    logger.warning(f"Index job {job_id} was cancelled mid-execution.")
                    job.status = IndexJobStatus.CANCELLED.value
                    self.db.commit()
                    return job

                filepath = change.path
                status = change.status

                if status == "deleted":
                    if hasattr(self.vector_store, "delete_by_metadata"):
                        self.vector_store.delete_by_metadata(
                            repo_id=repo_id,
                            filepath=filepath,
                            organization_id=org_id,
                            hard_delete=True,
                        )
                    self.db.query(FileIndexRecord).filter(
                        FileIndexRecord.organization_id == org_id,
                        FileIndexRecord.repository_id == repo_id,
                        FileIndexRecord.filepath == filepath,
                    ).delete()
                    job.files_deleted += 1

                else:
                    content = change.content
                    current_hash = self.compute_hash(content)

                    existing_record = (
                        self.db.query(FileIndexRecord)
                        .filter(
                            FileIndexRecord.organization_id == org_id,
                            FileIndexRecord.repository_id == repo_id,
                            FileIndexRecord.filepath == filepath,
                        )
                        .first()
                    )

                    if existing_record and existing_record.file_hash == current_hash:
                        job.files_skipped += 1
                    else:
                        if existing_record:
                            if hasattr(self.vector_store, "delete_by_metadata"):
                                self.vector_store.delete_by_metadata(
                                    repo_id=repo_id,
                                    filepath=filepath,
                                    organization_id=org_id,
                                    hard_delete=True,
                                )

                        chunks = self._chunk_content(filepath, content)

                        for chunk_idx, chunk_item in enumerate(chunks):
                            chunk_content = chunk_item.get("content", "")
                            vector = self._embed(chunk_content)

                            metadata = {
                                "organization_id": org_id,
                                "repository_id": repo_id,
                                "branch": branch,
                                "filepath": filepath,
                                "chunk_index": chunk_idx,
                                "symbol_name": chunk_item.get("symbol_name"),
                                "type": chunk_item.get("type"),
                                "start_line": chunk_item.get("start_line"),
                                "end_line": chunk_item.get("end_line"),
                                "commit_sha": commit_sha,
                                "embedding_version": job_version,
                            }

                            chunk_id = f"{repo_id}_{filepath}_{chunk_idx}"
                            if hasattr(self.vector_store, "upsert"):
                                self.vector_store.upsert(
                                    id=chunk_id,
                                    vector=vector,
                                    metadata=metadata,
                                    content=chunk_content,
                                )
                            job.chunks_created += 1

                        if not existing_record:
                            existing_record = FileIndexRecord(
                                organization_id=org_id,
                                repository_id=repo_id,
                                filepath=filepath,
                                file_hash=current_hash,
                                commit_sha=commit_sha,
                            )
                            self.db.add(existing_record)
                        else:
                            existing_record.file_hash = current_hash
                            existing_record.commit_sha = commit_sha

                        job.files_indexed += 1

                job.files_processed = idx
                job.progress_pct = (idx / job.total_files) * 100.0 if job.total_files > 0 else 100.0
                self.db.commit()

                if progress_callback:
                    try:
                        progress_callback(idx, job.total_files, job.progress_pct, filepath)
                    except Exception as cb_err:
                        logger.warning(f"Progress callback error: {cb_err}")

            job.status = IndexJobStatus.COMPLETED.value
            job.progress_pct = 100.0
            self.db.commit()
            return job

        except Exception as e:
            logger.error(f"Indexing error on job {job_id}: {e}")
            traceback.print_exc()
            job.status = IndexJobStatus.FAILED.value
            job.error_message = str(e)
            self.db.commit()
            raise

    def _chunk_content(self, filepath: str, content: str) -> List[Dict[str, Any]]:
        if filepath.endswith(".py"):
            return chunk_python_code(content, filepath)

        lines = content.splitlines()
        return [
            {
                "symbol_name": "file",
                "type": "Text",
                "content": content,
                "start_line": 1,
                "end_line": len(lines),
                "filepath": filepath,
            }
        ]

    def _embed(self, text: str) -> List[float]:
        if self.embedding_model and hasattr(self.embedding_model, "embed"):
            return self.embedding_model.embed(text)
        return [0.0] * 1536
