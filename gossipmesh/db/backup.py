import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from gossipmesh.core.config import settings

logger = logging.getLogger(__name__)


class BackupMetadata:
    def __init__(
        self,
        backup_id: str,
        timestamp: str,
        database: str,
        tables_included: List[str],
        checksum_sha256: str,
        is_encrypted: bool,
        version: str = "1.0",
    ):
        self.backup_id = backup_id
        self.timestamp = timestamp
        self.database = database
        self.tables_included = tables_included
        self.checksum_sha256 = checksum_sha256
        self.is_encrypted = is_encrypted
        self.version = version


class DatabaseBackupManager:
    """Manages full backups, restore testing, encryption, and tenant data extraction."""

    def __init__(
        self,
        backup_dir: Path | str = "./backups",
        encryption_key: Optional[str] = None,
    ):
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        raw_key = encryption_key or settings.ENCRYPTION_KEY
        if len(raw_key.encode("utf-8")) != 44:
            derived = hashlib.sha256(raw_key.encode("utf-8")).digest()
            self.cipher = Fernet(base64.urlsafe_b64encode(derived))
        else:
            self.cipher = Fernet(raw_key.encode("utf-8"))

    def create_snapshot(
        self,
        db_name: str = "gossipmesh",
        tables: Optional[List[str]] = None,
        data_dump: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Path, BackupMetadata]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        backup_id = f"backup_{db_name}_{timestamp}"
        enc_path = self.backup_dir / f"{backup_id}.enc"

        payload = data_dump if data_dump is not None else {"status": "snapshot", "db": db_name, "tables": tables or []}
        serialized = json.dumps(payload, indent=2, default=str).encode("utf-8")

        sha256 = hashlib.sha256(serialized).hexdigest()
        encrypted = self.cipher.encrypt(serialized)
        enc_path.write_bytes(encrypted)

        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=timestamp,
            database=db_name,
            tables_included=tables or list(payload.keys()),
            checksum_sha256=sha256,
            is_encrypted=True,
        )

        meta_path = self.backup_dir / f"{backup_id}.meta.json"
        meta_path.write_text(json.dumps(metadata.__dict__, indent=2), encoding="utf-8")

        return enc_path, metadata

    def verify_and_restore(
        self,
        backup_file: Path,
        meta_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        backup_path = Path(backup_file).resolve()
        if not backup_path.is_file():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        encrypted_bytes = backup_path.read_bytes()
        decrypted_bytes = self.cipher.decrypt(encrypted_bytes)

        if meta_file and Path(meta_file).is_file():
            meta_data = json.loads(Path(meta_file).read_text(encoding="utf-8"))
            expected_sha = meta_data.get("checksum_sha256")
            computed_sha = hashlib.sha256(decrypted_bytes).hexdigest()
            if expected_sha and computed_sha != expected_sha:
                raise ValueError(f"Integrity check failed: Expected {expected_sha}, computed {computed_sha}")

        return json.loads(decrypted_bytes.decode("utf-8"))

    def export_tenant_data(
        self,
        db_session: Session,
        organization_id: int,
        output_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        from gossipmesh.models.organization import Organization
        from gossipmesh.models.repository import Repository
        from gossipmesh.models.runtime import Budget, Workflow

        tenant = db_session.query(Organization).filter(Organization.id == organization_id).first()
        if not tenant:
            raise ValueError(f"Organization ID {organization_id} not found")

        users = getattr(tenant, "users", [])
        repos = db_session.query(Repository).filter(Repository.organization_id == organization_id).all()
        repo_ids = [r.id for r in repos]

        workflows = db_session.query(Workflow).filter(Workflow.repository_id.in_(repo_ids)).all() if repo_ids else []
        budget = db_session.query(Budget).filter(Budget.organization_id == organization_id).first()

        tenant_slug = getattr(tenant, "slug", getattr(tenant, "name", "").lower())
        tenant_export = {
            "metadata": {
                "organization_id": organization_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0",
            },
            "organization": {
                "id": tenant.id,
                "name": tenant.name,
                "slug": tenant_slug,
                "created_at": str(tenant.created_at) if hasattr(tenant, "created_at") else None,
            },
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "is_active": u.is_active,
                    "role": getattr(u, "role", "member"),
                }
                for u in users
            ],
            "repositories": [
                {
                    "id": r.id,
                    "name": r.name,
                    "full_name": r.full_name,
                    "provider": getattr(r, "provider", "github"),
                }
                for r in repos
            ],
            "workflows": [
                {
                    "id": w.id,
                    "repository_id": w.repository_id,
                    "status": getattr(w, "status", "completed"),
                    "created_at": str(w.created_at) if hasattr(w, "created_at") else None,
                }
                for w in workflows
            ],
            "budget": {
                "monthly_limit_usd": budget.monthly_limit_usd if budget else None,
                "current_spend_usd": budget.current_spend_usd if budget else None,
            }
            if budget
            else None,
        }

        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            Path(output_file).write_text(json.dumps(tenant_export, indent=2), encoding="utf-8")

        return tenant_export
