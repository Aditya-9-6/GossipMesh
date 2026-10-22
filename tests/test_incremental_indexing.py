"""Unit tests for Incremental Indexing Engine (Task 76)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.models.base import Base
from gossipmesh.models.indexing import FileIndexRecord, IndexJob, IndexJobStatus
from gossipmesh.repository.indexing import FileChange, IncrementalIndexer
from gossipmesh.repository.vector_store import DocumentChunk, PGVectorStore


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_incremental_indexing_skips_unchanged_files(db_session):
    """Verify unchanged files with matching content hash are skipped on subsequent syncs."""
    vector_store = PGVectorStore(db_session)
    indexer = IncrementalIndexer(vector_store=vector_store, db_session=db_session)

    # Initial Sync: 2 new files
    job1 = indexer.create_index_job(organization_id="org-1", repository_id=101, commit_sha="commit-aaa")
    changes_run1 = [
        FileChange(path="src/main.py", content="def main(): pass", status="added"),
        FileChange(path="src/utils.py", content="def helper(): return 42", status="added"),
    ]

    res1 = indexer.sync_repository(job1.id, changes_run1)
    assert res1.status == IndexJobStatus.COMPLETED.value
    assert res1.files_indexed == 2
    assert res1.files_skipped == 0
    assert res1.chunks_created >= 2

    # Second Sync: main.py unchanged, utils.py modified
    job2 = indexer.create_index_job(organization_id="org-1", repository_id=101, commit_sha="commit-bbb")
    changes_run2 = [
        FileChange(path="src/main.py", content="def main(): pass", status="modified"),
        FileChange(path="src/utils.py", content="def helper(): return 99  # updated", status="modified"),
    ]

    res2 = indexer.sync_repository(job2.id, changes_run2)
    assert res2.status == IndexJobStatus.COMPLETED.value
    assert res2.files_indexed == 1  # only utils.py re-indexed
    assert res2.files_skipped == 1  # main.py skipped!


def test_deleted_file_purges_chunks(db_session):
    """Verify that deleting a file purges its chunks from the vector store and tracking records."""
    vector_store = PGVectorStore(db_session)
    indexer = IncrementalIndexer(vector_store=vector_store, db_session=db_session)

    # Index initial file
    job1 = indexer.create_index_job(organization_id="org-1", repository_id=102, commit_sha="c1")
    indexer.sync_repository(job1.id, [FileChange(path="src/legacy.py", content="def old(): pass", status="added")])

    chunks_before = db_session.query(DocumentChunk).filter(DocumentChunk.filepath == "src/legacy.py").count()
    assert chunks_before > 0

    # Delete the file
    job2 = indexer.create_index_job(organization_id="org-1", repository_id=102, commit_sha="c2")
    res2 = indexer.sync_repository(job2.id, [FileChange(path="src/legacy.py", status="deleted")])

    assert res2.files_deleted == 1
    chunks_after = db_session.query(DocumentChunk).filter(DocumentChunk.filepath == "src/legacy.py").count()
    assert chunks_after == 0

    record = db_session.query(FileIndexRecord).filter(FileIndexRecord.filepath == "src/legacy.py").first()
    assert record is None


def test_cooperative_cancellation(db_session):
    """Verify that cancellation flag halts the indexing job."""
    vector_store = PGVectorStore(db_session)
    indexer = IncrementalIndexer(vector_store=vector_store, db_session=db_session)

    job = indexer.create_index_job(organization_id="org-1", repository_id=103, commit_sha="c3")

    # Cancel immediately before or during execution
    indexer.cancel_job(job.id)

    changes = [
        FileChange(path="file1.py", content="def f1(): pass"),
        FileChange(path="file2.py", content="def f2(): pass"),
    ]

    res = indexer.sync_repository(job.id, changes)
    assert res.status == IndexJobStatus.CANCELLED.value
    assert res.files_indexed == 0


def test_progress_reporting_callback(db_session):
    """Verify progress callback is triggered per file."""
    vector_store = PGVectorStore(db_session)
    indexer = IncrementalIndexer(vector_store=vector_store, db_session=db_session)

    job = indexer.create_index_job(organization_id="org-1", repository_id=104, commit_sha="c4")

    progress_events = []

    def on_progress(processed, total, pct, current_file):
        progress_events.append((processed, total, round(pct, 1), current_file))

    changes = [
        FileChange(path="a.py", content="def a(): pass"),
        FileChange(path="b.py", content="def b(): pass"),
    ]

    indexer.sync_repository(job.id, changes, progress_callback=on_progress)
    assert len(progress_events) == 2
    assert progress_events[0] == (1, 2, 50.0, "a.py")
    assert progress_events[1] == (2, 2, 100.0, "b.py")
