"""Enterprise Idempotency Engine (Task 59).

Guarantees exactly-once semantics across:
1. Workflow creation
2. Webhook jobs
3. PR review comments
4. Pull Request creation
5. Usage metering & billing charges
6. Artifact upload and quarantine operations
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from gossipmesh.core.exceptions import ConflictError, AuthorizationError
from gossipmesh.models.idempotency import IdempotencyRecord

logger = logging.getLogger(__name__)


class IdempotencyScope(str, Enum):
    WORKFLOW_CREATION = "workflow_creation"
    WEBHOOK_JOB = "webhook_job"
    COMMENTS = "comment_creation"
    PR_CREATION = "pr_creation"
    BILLING_USAGE = "billing_usage"
    ARTIFACT_OPERATION = "artifact_operation"


class IdempotencyStatus(str, Enum):
    ACQUIRED = "acquired"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"


class IdempotencyEngine:
    """Manages transactional idempotency keys, duplicate suppression, and response caching."""

    @staticmethod
    def compute_request_hash(payload: Any) -> str:
        """Computes a deterministic SHA-256 hash of the canonical request payload."""
        if payload is None:
            canonical_bytes = b""
        elif isinstance(payload, bytes):
            canonical_bytes = payload
        elif isinstance(payload, str):
            canonical_bytes = payload.encode("utf-8")
        else:
            try:
                canonical_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            except Exception:
                canonical_bytes = str(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    @classmethod
    def acquire(
        cls,
        db: Session,
        key: str,
        scope: str,
        payload: Any,
        organization_id: Optional[int] = None,
        ttl_seconds: int = 86400,
        lock_timeout_seconds: int = 60,
    ) -> Tuple[IdempotencyStatus, Optional[Dict[str, Any]], Optional[int]]:
        """Acquires an idempotency key.

        Returns:
            (status, response_body, response_code)
            - If ACQUIRED: The caller should proceed with execution.
            - If COMPLETED: The caller must return the cached response immediately without re-executing.
            - Raises ConflictError: If the idempotency key was previously used with a different payload.
            - Raises ConflictError: If another concurrent process is currently executing this request (lock active).
        """
        now = datetime.now(timezone.utc)
        request_hash = cls.compute_request_hash(payload)

        record = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()

        if record is not None:
            # 1. Payload mismatch check
            if record.request_hash != request_hash:
                raise ConflictError(
                    message=f"Idempotency key '{key}' was previously used with a different request payload."
                )

            # 2. Scope mismatch check
            if record.scope != scope:
                raise ConflictError(
                    message=f"Idempotency key '{key}' was previously used with a different scope ('{record.scope}')."
                )

            # 3. Already completed -> return cached response
            if record.status == "completed":
                return IdempotencyStatus.COMPLETED, record.response_body, record.response_code

            # 4. In-progress check
            locked_until = record.locked_until
            if locked_until and locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)

            if locked_until and locked_until > now:
                raise ConflictError(message=f"Concurrent operation in progress for idempotency key '{key}'.")

            # Lock expired -> renew lock and re-acquire
            record.status = "in_progress"
            record.locked_until = now + timedelta(seconds=lock_timeout_seconds)
            record.expires_at = now + timedelta(seconds=ttl_seconds)
            db.commit()
            return IdempotencyStatus.ACQUIRED, None, None

        # Create new idempotency key
        new_record = IdempotencyRecord(
            key=key,
            scope=scope,
            organization_id=organization_id,
            request_hash=request_hash,
            status="in_progress",
            locked_until=now + timedelta(seconds=lock_timeout_seconds),
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        db.add(new_record)
        db.commit()
        return IdempotencyStatus.ACQUIRED, None, None

    @staticmethod
    def complete(
        db: Session,
        key: str,
        response_body: Any,
        response_code: int = 200,
    ) -> None:
        """Marks the idempotency key as completed and persists the response for subsequent retries."""
        record = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()
        if record:
            record.status = "completed"
            record.response_code = response_code
            record.response_body = response_body if isinstance(response_body, dict) else {"result": response_body}
            record.locked_until = None
            db.commit()

    @staticmethod
    def fail(db: Session, key: str, allow_retry: bool = True) -> None:
        """Releases the lock on failure, optionally allowing immediate retry or marking failed."""
        record = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()
        if record:
            if allow_retry:
                # Delete or reset so subsequent attempt can retry immediately
                db.delete(record)
            else:
                record.status = "failed"
                record.locked_until = None
            db.commit()


class IdempotencyContext:
    """Context manager for transparent idempotent execution."""

    def __init__(
        self,
        db: Session,
        key: str,
        scope: str,
        payload: Any = None,
        organization_id: Optional[int] = None,
        ttl_seconds: int = 86400,
    ):
        self.db = db
        self.key = key
        self.scope = scope
        self.payload = payload
        self.organization_id = organization_id
        self.ttl_seconds = ttl_seconds

        self.status: Optional[IdempotencyStatus] = None
        self.cached_response: Optional[Dict[str, Any]] = None
        self.cached_code: Optional[int] = None

    @property
    def is_cached(self) -> bool:
        return self.status == IdempotencyStatus.COMPLETED

    def __enter__(self):
        self.status, self.cached_response, self.cached_code = IdempotencyEngine.acquire(
            db=self.db,
            key=self.key,
            scope=self.scope,
            payload=self.payload,
            organization_id=self.organization_id,
            ttl_seconds=self.ttl_seconds,
        )
        return self

    def complete(self, response: Any, code: int = 200):
        if not self.is_cached:
            IdempotencyEngine.complete(self.db, self.key, response, code)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and not self.is_cached:
            IdempotencyEngine.fail(self.db, self.key, allow_retry=True)
