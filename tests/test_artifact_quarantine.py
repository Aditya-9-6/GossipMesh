"""Unit tests for Artifact Quarantine and Malware Defense System (Task 84)."""

from datetime import datetime, timedelta, timezone
import os
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.core.exceptions import AuthorizationError, ValidationError
from gossipmesh.models.base import Base
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.runtime import Artifact, Job, Workflow
from gossipmesh.models.user import User
from gossipmesh.models.repository import Repository
from gossipmesh.runtime.quarantine import (
    ArtifactQuarantineManager,
    EICAR_SIGNATURE,
    MalwareScanner,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create Org, User, Repo, Workflow, Job fixtures
    org1 = Organization(id=1, name="Org One")
    org2 = Organization(id=2, name="Org Two")
    user1 = User(id=1, email="user1@org1.com", hashed_password="pwd", is_superuser=False)
    user2 = User(id=2, email="user2@org2.com", hashed_password="pwd", is_superuser=False)
    repo = Repository(id=10, organization_id=1, github_id=1001, name="repo1", full_name="org1/repo1")
    wf = Workflow(id=100, organization_id=1, repository_id=10)
    job = Job(id=500, workflow_id=100, agent_name="test_runner")

    session.add_all([org1, org2, user1, user2, repo, wf, job])
    session.add(UserOrganization(user_id=1, organization_id=1))
    session.add(UserOrganization(user_id=2, organization_id=2))
    session.commit()

    yield session
    session.close()


def test_clean_artifact_storage_and_quarantine_pass(db_session):
    """Verify storing a clean test report artifact passes quarantine checks."""
    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)
        content = b'{"coverage": 98.5, "passed": 42}'

        artifact = manager.store_and_quarantine(
            organization_id=1,
            job_id=500,
            name="coverage.json",
            content_bytes=content,
            db=db_session,
        )

        assert artifact.id is not None
        assert artifact.quarantine_status == "CLEAN"
        assert artifact.size_bytes == len(content)
        assert artifact.content_type == "application/json"
        assert artifact.sha256_hash is not None
        assert artifact.scan_results["is_infected"] is False
        assert os.path.exists(artifact.storage_path)


def test_malware_eicar_signature_detection_and_quarantine(db_session):
    """Verify EICAR signature is detected and flagged as INFECTED."""
    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)
        malicious_content = b"Harmless prefix " + EICAR_SIGNATURE

        artifact = manager.store_and_quarantine(
            organization_id=1,
            job_id=500,
            name="test_report.txt",
            content_bytes=malicious_content,
            db=db_session,
        )

        assert artifact.quarantine_status == "INFECTED"
        assert artifact.scan_results["is_infected"] is True
        assert artifact.scan_results["signature"] == "EICAR_TEST_VIRUS"

        # Attempting download of infected artifact MUST fail
        user1 = db_session.query(User).filter(User.id == 1).first()
        with pytest.raises(AuthorizationError) as exc_info:
            manager.authorize_and_download(artifact.id, user1, db_session)
        assert "is INFECTED" in str(exc_info.value.message)


def test_executable_binary_header_detection(db_session):
    """Verify embedded Linux ELF or Windows PE binaries in artifacts are flagged."""
    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)
        elf_content = b"\x7fELF\x02\x01\x01" + b"\x00" * 32

        artifact = manager.store_and_quarantine(
            organization_id=1,
            job_id=500,
            name="data.txt",
            content_bytes=elf_content,
            db=db_session,
        )

        assert artifact.quarantine_status == "INFECTED"
        assert "EXECUTABLE_BINARY_PAYLOAD" in artifact.scan_results["signature"]


def test_forbidden_extension_rejected(db_session):
    """Verify executables and shell scripts are rejected by extension policy."""
    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)

        with pytest.raises(ValidationError) as exc_info:
            manager.store_and_quarantine(
                organization_id=1,
                job_id=500,
                name="payload.exe",
                content_bytes=b"dummy",
                db=db_session,
            )
        assert "is forbidden" in str(exc_info.value.message)


def test_cross_tenant_download_blocked(db_session):
    """Verify user from Org 2 cannot download Org 1's artifact."""
    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)

        artifact = manager.store_and_quarantine(
            organization_id=1,
            job_id=500,
            name="secret_report.md",
            content_bytes=b"# Org 1 Report",
            db=db_session,
        )

        user2 = db_session.query(User).filter(User.id == 2).first()
        with pytest.raises(AuthorizationError) as exc_info:
            manager.authorize_and_download(artifact.id, user2, db_session)
        assert "Not authorized" in str(exc_info.value.message)


def test_download_auditing_and_count(db_session):
    """Verify download count is incremented on delivery."""
    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)

        artifact = manager.store_and_quarantine(
            organization_id=1,
            job_id=500,
            name="valid.json",
            content_bytes=b'{"status": "ok"}',
            db=db_session,
        )

        user1 = db_session.query(User).filter(User.id == 1).first()
        _, content = manager.authorize_and_download(artifact.id, user1, db_session)

        assert content == b'{"status": "ok"}'
        assert artifact.download_count == 1


def test_retention_cleanup(db_session):
    """Verify expired artifacts are cleaned up."""
    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)

        artifact = manager.store_and_quarantine(
            organization_id=1,
            job_id=500,
            name="temporary.log",
            content_bytes=b"log data",
            db=db_session,
        )

        # Force expiration in past
        artifact.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        count = manager.cleanup_expired_artifacts(db_session)
        assert count == 1
        assert artifact.deleted_at is not None
        assert artifact.quarantine_status == "EXPIRED"
