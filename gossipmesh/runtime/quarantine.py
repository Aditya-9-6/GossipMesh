"""Enterprise Artifact Quarantine and Malware Defense System (Task 84).

Enforces:
- Tenant-scoped storage hierarchy (<root>/org_<id>/job_<id>/<hash>_<name>)
- File size validation (max 50 MB) and extension whitelisting
- Malware scanning (EICAR signature, ELF/PE/Mach-O executable headers, shell wrappers)
- Cryptographic SHA-256 integrity hashing
- Quarantine state machine (QUARANTINED -> CLEAN | INFECTED -> EXPIRED)
- Strict access authorization and download audit logging
- Automatic retention policy cleanup
"""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import mimetypes
import os
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import AuthorizationError, ValidationError
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.runtime import Artifact
from gossipmesh.models.user import User

logger = logging.getLogger(__name__)

# Standard EICAR antivirus test signature
EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

# Executable magic byte headers forbidden in test/report artifacts
EXECUTABLE_HEADERS = [
    (b"\x7fELF", "Linux ELF Binary"),
    (b"MZ", "Windows PE Executable / DLL"),
    (b"\xfe\xed\xfa\xce", "Mach-O 32-bit Binary"),
    (b"\xfe\xed\xfa\xcf", "Mach-O 64-bit Binary"),
    (b"\xcf\xfa\xed\xfe", "Mach-O Universal Binary"),
]

ALLOWED_EXTENSIONS: Set[str] = {
    ".json",
    ".txt",
    ".diff",
    ".patch",
    ".md",
    ".xml",
    ".log",
    ".csv",
    ".tar.gz",
    ".zip",
    ".pdf",
    ".html",
    ".coverage",
}

BLOCKED_EXTENSIONS: Set[str] = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".sh",
    ".bash",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".jar",
    ".msi",
}


class MalwareScanResult:
    def __init__(self, is_infected: bool, signature: Optional[str] = None, details: Optional[str] = None):
        self.is_infected = is_infected
        self.signature = signature
        self.details = details or ("Infected file" if is_infected else "Clean file")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_infected": self.is_infected,
            "signature": self.signature,
            "details": self.details,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }


class MalwareScanner:
    """Deterministic antivirus and payload scanner for quarantined artifacts."""

    @classmethod
    def scan_bytes(cls, content: bytes, filename: str) -> MalwareScanResult:
        # 1. EICAR test signature
        if EICAR_SIGNATURE in content:
            return MalwareScanResult(
                is_infected=True, signature="EICAR_TEST_VIRUS", details="Standard EICAR test file detected"
            )

        # 2. Executable magic headers
        if len(content) >= 4:
            for header, desc in EXECUTABLE_HEADERS:
                if content.startswith(header):
                    return MalwareScanResult(
                        is_infected=True,
                        signature="EXECUTABLE_BINARY_PAYLOAD",
                        details=f"Forbidden binary format: {desc}",
                    )

        # 3. Shell script header in non-script artifact
        if content.startswith(b"#!/bin/bash") or content.startswith(b"#!/bin/sh"):
            return MalwareScanResult(
                is_infected=True,
                signature="SHELL_SCRIPT_IN_ARTIFACT",
                details="Embedded shell script detected in artifact",
            )

        return MalwareScanResult(is_infected=False, details="No malware signatures detected")


class ArtifactQuarantineManager:
    """Manages the full lifecycle of tenant-isolated quarantined artifacts."""

    MAX_ARTIFACT_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    def __init__(self, base_storage_dir: Optional[str] = None):
        self.base_storage_dir = base_storage_dir or os.getenv(
            "ARTIFACT_STORAGE_DIR", os.path.abspath(".gossipmesh_artifacts")
        )
        os.makedirs(self.base_storage_dir, exist_ok=True)

    def store_and_quarantine(
        self,
        organization_id: int,
        job_id: int,
        name: str,
        content_bytes: bytes,
        db: Session,
        retention_days: int = 30,
    ) -> Artifact:
        """
        Validates, scans, and stores an artifact in tenant-scoped storage.
        Quarantines immediately if malware signatures are identified.
        """
        # 1. Size Validation
        size = len(content_bytes)
        if size > self.MAX_ARTIFACT_SIZE_BYTES:
            raise ValidationError(
                message=f"Artifact '{name}' exceeds maximum allowed size ({self.MAX_ARTIFACT_SIZE_BYTES // (1024 * 1024)} MB)"
            )

        # 2. Type & Extension Validation
        ext = os.path.splitext(name)[1].lower()
        if ext in BLOCKED_EXTENSIONS or (ext and ext not in ALLOWED_EXTENSIONS):
            raise ValidationError(message=f"Artifact extension '{ext}' is forbidden by sandbox security policy.")

        content_type, _ = mimetypes.guess_type(name)
        content_type = content_type or "application/octet-stream"

        # 3. SHA-256 Checksum
        sha256 = hashlib.sha256(content_bytes).hexdigest()

        # 4. Malware Scanning
        scan = MalwareScanner.scan_bytes(content_bytes, name)
        quarantine_status = "INFECTED" if scan.is_infected else "CLEAN"

        if scan.is_infected:
            logger.critical(
                f"[SECURITY_ALERT:INFECTED_ARTIFACT] org_id={organization_id} job_id={job_id} "
                f"file={name} signature={scan.signature}"
            )

        # 5. Tenant-Isolated Storage Hierarchy
        # <base>/org_<id>/job_<id>/<sha256>_<sanitized_name>
        safe_filename = "".join(c for c in name if c.isalnum() or c in "._-")
        tenant_dir = os.path.join(self.base_storage_dir, f"org_{organization_id}", f"job_{job_id}")
        os.makedirs(tenant_dir, exist_ok=True)

        storage_path = os.path.join(tenant_dir, f"{sha256[:12]}_{safe_filename}")
        with open(storage_path, "wb") as f:
            f.write(content_bytes)

        # 6. Database Record Persistence
        expires_at = datetime.now(timezone.utc) + timedelta(days=retention_days)
        artifact = Artifact(
            organization_id=organization_id,
            job_id=job_id,
            name=name,
            storage_path=storage_path,
            size_bytes=size,
            content_type=content_type,
            sha256_hash=sha256,
            quarantine_status=quarantine_status,
            scan_results=scan.to_dict(),
            retention_days=retention_days,
            expires_at=expires_at,
            download_count=0,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        return artifact

    def authorize_and_download(
        self,
        artifact_id: int,
        user: User,
        db: Session,
    ) -> Tuple[Artifact, bytes]:
        """
        Authorizes user membership and verifies clean quarantine status before delivering content.
        Emits structured audit log for every download.
        """
        artifact = db.query(Artifact).filter(Artifact.id == artifact_id, Artifact.deleted_at.is_(None)).first()
        if not artifact:
            raise ValidationError(message="Artifact not found")

        # 1. Organization Authorization
        if not user.is_superuser:
            membership = (
                db.query(UserOrganization)
                .filter(
                    UserOrganization.user_id == user.id,
                    UserOrganization.organization_id == artifact.organization_id,
                )
                .first()
            )
            if not membership:
                raise AuthorizationError(message="Not authorized to access this organization's artifacts")

        # 2. Quarantine Status Enforcement
        if artifact.quarantine_status != "CLEAN":
            raise AuthorizationError(
                message=f"Access blocked: Artifact '{artifact.name}' is {artifact.quarantine_status}."
            )

        # 3. Read file content
        if not os.path.exists(artifact.storage_path):
            raise ValidationError(message="Artifact file missing from storage partition")

        with open(artifact.storage_path, "rb") as f:
            content = f.read()

        # 4. Download Audit Logging
        artifact.download_count += 1
        db.commit()

        logger.info(
            f"[AUDIT:ARTIFACT_DOWNLOAD] user_id={user.id} artifact_id={artifact.id} "
            f"org_id={artifact.organization_id} size={artifact.size_bytes} download_num={artifact.download_count}"
        )

        return artifact, content

    def cleanup_expired_artifacts(self, db: Session) -> int:
        """Removes expired artifacts past their retention date from storage and marks them deleted."""
        now = datetime.now(timezone.utc)
        expired = (
            db.query(Artifact)
            .filter(
                Artifact.expires_at.isnot(None),
                Artifact.expires_at <= now,
                Artifact.deleted_at.is_(None),
            )
            .all()
        )

        count = 0
        for art in expired:
            if os.path.exists(art.storage_path):
                try:
                    os.remove(art.storage_path)
                except Exception as e:
                    logger.warning(f"Error removing expired artifact file {art.storage_path}: {e}")
            art.deleted_at = now
            art.quarantine_status = "EXPIRED"
            count += 1

        db.commit()
        return count
