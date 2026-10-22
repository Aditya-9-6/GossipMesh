import json
import pytest
from unittest.mock import MagicMock
from pathlib import Path

from gossipmesh.db.backup import DatabaseBackupManager, BackupMetadata
from gossipmesh.models.organization import Organization
from gossipmesh.models.user import User
from gossipmesh.models.repository import Repository
from gossipmesh.models.runtime import Workflow, Budget


def test_backup_create_encrypt_and_restore(tmp_path):
    mgr = DatabaseBackupManager(backup_dir=tmp_path)
    sample_data = {
        "users": [{"id": 1, "email": "admin@gossipmesh.io"}],
        "organizations": [{"id": 10, "name": "Acme Corp"}],
        "system_status": "healthy",
    }

    # 1. Create encrypted snapshot
    enc_path, metadata = mgr.create_snapshot(db_name="test_db", data_dump=sample_data)
    assert enc_path.is_file()
    assert metadata.checksum_sha256 is not None
    assert metadata.is_encrypted is True

    # 2. Verify and restore
    restored = mgr.verify_and_restore(enc_path)
    assert restored["system_status"] == "healthy"
    assert restored["users"][0]["email"] == "admin@gossipmesh.io"


def test_backup_tamper_detection(tmp_path):
    mgr = DatabaseBackupManager(backup_dir=tmp_path)
    sample_data = {"key": "original_unmodified_value"}

    enc_path, metadata = mgr.create_snapshot(db_name="tamper_test", data_dump=sample_data)
    meta_path = tmp_path / f"{metadata.backup_id}.meta.json"

    # Modify expected sha in metadata to simulate corruption
    corrupt_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    corrupt_meta["checksum_sha256"] = "badc0ffee" * 7
    meta_path.write_text(json.dumps(corrupt_meta), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        mgr.verify_and_restore(enc_path, meta_file=meta_path)
    assert "Integrity check failed" in str(exc.value)


def test_tenant_data_export_isolation(tmp_path):
    mgr = DatabaseBackupManager(backup_dir=tmp_path)

    # Setup mock DB session
    mock_session = MagicMock()

    org_tenant = MagicMock(spec=Organization)
    org_tenant.id = 42
    org_tenant.name = "Tenant 42 Corp"
    org_tenant.slug = "tenant-42"
    org_tenant.created_at = "2026-10-01T00:00:00Z"

    user_tenant = MagicMock(spec=User)
    user_tenant.id = 101
    user_tenant.email = "tenant42_admin@example.com"
    user_tenant.is_active = True
    user_tenant.role = "admin"

    org_tenant.users = [user_tenant]

    repo_tenant = MagicMock(spec=Repository)
    repo_tenant.id = 201
    repo_tenant.name = "repo-42"
    repo_tenant.full_name = "tenant-42/repo-42"
    repo_tenant.organization_id = 42

    def fake_query(model):
        q = MagicMock()
        if model == Organization:
            q.filter.return_value.first.return_value = org_tenant
        elif model == User:
            q.filter.return_value.all.return_value = [user_tenant]
        elif model == Repository:
            q.filter.return_value.all.return_value = [repo_tenant]
        elif model == Workflow:
            q.filter.return_value.all.return_value = []
        elif model == Budget:
            q.filter.return_value.first.return_value = None
        return q

    mock_session.query.side_effect = fake_query

    export_out = tmp_path / "tenant_export.json"
    result = mgr.export_tenant_data(mock_session, organization_id=42, output_file=export_out)

    assert result["metadata"]["organization_id"] == 42
    assert result["organization"]["name"] == "Tenant 42 Corp"
    assert len(result["users"]) == 1
    assert result["users"][0]["email"] == "tenant42_admin@example.com"
    assert len(result["repositories"]) == 1
    assert export_out.is_file()
