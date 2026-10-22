"""
Immutable Audit Trail Service (Task 108).

Audits login, failures, roles, repository connections, provider credentials,
reviews, findings, approvals, sandbox work, exports, deletions, billing,
and support access with tamper-evident records and secret redaction.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import ValidationError
from gossipmesh.core.logging import redact_sensitive_data
from gossipmesh.models.audit import AuditEvent


class AuditAction(str, Enum):
    AUTH_LOGIN = "auth.login"
    AUTH_FAILURE = "auth.failure"
    ROLE_CHANGED = "organization.role_changed"
    REPO_CONNECTED = "repository.connected"
    PROVIDER_CREDENTIAL_UPDATED = "provider.credential_updated"
    REVIEW_DISPATCHED = "review.dispatched"
    FINDING_MODIFIED = "finding.modified"
    APPROVAL_GRANTED = "approval.granted"
    SANDBOX_EXECUTED = "sandbox.executed"
    DATA_EXPORTED = "tenant.data_exported"
    DATA_DELETED = "tenant.data_deleted"
    BILLING_MUTATED = "billing.mutated"
    SUPPORT_ACCESS_GRANTED = "support.access_granted"


# Prevent updates or deletes on AuditEvent records in ORM
@event.listens_for(AuditEvent, "before_update")
def _prevent_audit_update(mapper, connection, target):
    raise ValidationError("AuditEvent records are append-only and strictly immutable. Updates are forbidden.")


@event.listens_for(AuditEvent, "before_delete")
def _prevent_audit_delete(mapper, connection, target):
    raise ValidationError("AuditEvent records are append-only and strictly immutable. Deletions are forbidden.")


class ImmutableAuditService:
    """Manages creation and querying of immutable compliance audit events."""

    @staticmethod
    def record_event(
        session: Session,
        action: AuditAction | str,
        organization_id: Optional[int],
        actor_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Creates an immutable, sanitized audit record.
        """
        act_str = action.value if isinstance(action, AuditAction) else str(action)

        # Sanitize details to guarantee zero secret leakage
        sanitized_details = None
        if details:
            serialized = json.dumps(details)
            clean_serialized = redact_sensitive_data(serialized)
            sanitized_details = json.loads(clean_serialized)

        event_obj = AuditEvent(
            action=act_str,
            actor_id=actor_id,
            organization_id=organization_id,
            details=sanitized_details,
        )
        session.add(event_obj)
        session.commit()
        session.refresh(event_obj)
        return event_obj

    @staticmethod
    def query_audit_trail(
        session: Session,
        organization_id: Optional[int] = None,
        action: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEvent]:
        """Queries audit trail with optional organization and action filters."""
        stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc())
        if organization_id is not None:
            stmt = stmt.where(AuditEvent.organization_id == organization_id)
        if action is not None:
            stmt = stmt.where(AuditEvent.action == action)
        stmt = stmt.limit(limit)
        return list(session.execute(stmt).scalars().all())
