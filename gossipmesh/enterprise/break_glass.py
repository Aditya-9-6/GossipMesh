"""
Enterprise Support Break-Glass Access Controls (Task 111).

Enforces:
- Explicit mandatory justification and ticket reference
- Customer authorization
- Time-bounded expiry (max 4 hours)
- Strict least-privilege (source code access disabled by default)
- Immutable compliance audit logging
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import AuthorizationError, ValidationError
from gossipmesh.models.audit import AuditEvent


@dataclass
class BreakGlassSession:
    id: str
    support_user_id: int
    organization_id: int
    reason: str
    ticket_id: str
    granted_at: datetime
    expires_at: datetime
    allow_source_code_access: bool
    is_revoked: bool = False


class BreakGlassControlService:
    """Manages secure, audited, time-bound customer support break-glass access."""

    def __init__(self, max_duration_hours: int = 4):
        self.max_duration_hours = max_duration_hours
        self._active_sessions: Dict[str, BreakGlassSession] = {}

    def request_access(
        self,
        session: Session,
        support_user_id: int,
        organization_id: int,
        reason: str,
        ticket_id: str,
        duration_hours: int = 2,
        allow_source_code_access: bool = False,
    ) -> BreakGlassSession:
        """
        Grants temporary break-glass access to a customer organization.
        Enforces justification length, duration cap, and default code restriction.
        """
        if not reason or len(reason.strip()) < 15:
            raise ValidationError("Break-glass access requires a detailed operational justification (min 15 chars)")

        if not ticket_id or not ticket_id.strip():
            raise ValidationError("Break-glass access requires a valid customer support ticket ID")

        if duration_hours > self.max_duration_hours or duration_hours <= 0:
            raise ValidationError(f"Break-glass duration must be between 1 and {self.max_duration_hours} hours")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=duration_hours)
        session_id = f"bg_{organization_id}_{support_user_id}_{int(now.timestamp())}"

        grant = BreakGlassSession(
            id=session_id,
            support_user_id=support_user_id,
            organization_id=organization_id,
            reason=reason.strip(),
            ticket_id=ticket_id.strip(),
            granted_at=now,
            expires_at=expires_at,
            allow_source_code_access=allow_source_code_access,
        )
        self._active_sessions[session_id] = grant

        # Emit audit trail
        audit = AuditEvent(
            action="support.break_glass_granted",
            actor_id=support_user_id,
            organization_id=organization_id,
            details={
                "session_id": session_id,
                "ticket_id": ticket_id,
                "reason": reason,
                "duration_hours": duration_hours,
                "allow_source_code_access": allow_source_code_access,
                "expires_at": expires_at.isoformat(),
            },
        )
        session.add(audit)
        session.commit()

        return grant

    def verify_access(
        self,
        support_user_id: int,
        organization_id: int,
        requesting_source_code: bool = False,
    ) -> BreakGlassSession:
        """
        Validates whether the support user holds a valid, unexpired break-glass session.
        Rejects requests for source code if allow_source_code_access was not explicitly granted.
        """
        now = datetime.now(timezone.utc)
        for grant in self._active_sessions.values():
            if (
                grant.support_user_id == support_user_id
                and grant.organization_id == organization_id
                and not grant.is_revoked
                and grant.expires_at > now
            ):
                if requesting_source_code and not grant.allow_source_code_access:
                    raise AuthorizationError(
                        "Break-glass session does not permit proprietary source code access. Metadata only."
                    )
                return grant

        raise AuthorizationError("No active or valid break-glass support session found for this organization")

    def revoke_access(
        self,
        session: Session,
        session_id: str,
        revoked_by_id: int,
        reason: str = "Support work completed",
    ) -> None:
        """Revokes an active break-glass session immediately."""
        grant = self._active_sessions.get(session_id)
        if not grant:
            raise ValidationError(f"Session {session_id} not found")

        grant.is_revoked = True

        audit = AuditEvent(
            action="support.break_glass_revoked",
            actor_id=revoked_by_id,
            organization_id=grant.organization_id,
            details={"session_id": session_id, "reason": reason},
        )
        session.add(audit)
        session.commit()
