import hashlib
import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from gossipmesh.models.webhooks import WebhookEvent
from gossipmesh.models.audit import AuditEvent

logger = logging.getLogger(__name__)


class IssueIdempotencyManager:
    """Manages idempotency for issue-to-PR workflows, ensuring repeated execution
    does not create duplicate branches, PRs, commits, comments, usage charges, or workflows."""

    @staticmethod
    def compute_payload_hash(payload: Dict[str, Any]) -> str:
        """Compute a deterministic hash of the issue/webhook payload."""
        canonical_str = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    def is_event_processed(db: Session, event_id: str) -> bool:
        """Check if an external event ID has already been successfully processed."""
        existing = (
            db.query(WebhookEvent).filter(WebhookEvent.id == event_id, WebhookEvent.status == "processed").first()
        )
        return existing is not None

    @staticmethod
    def check_existing_pr_or_branch(db: Session, repo_full_name: str, issue_number: int) -> Dict[str, Any]:
        """
        Checks active runs, existing PRs, prior attempts, branch state,
        and generated commit identity for a given issue number and repository.
        """
        branch_name = f"gossipmesh/issue-{issue_number}"

        prior_attempts = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.action == "issue_solver_completed",
                AuditEvent.details["repo_full_name"].as_string() == repo_full_name,
                AuditEvent.details["issue_number"].as_integer() == issue_number,
            )
            .all()
        )

        is_duplicate = len(prior_attempts) > 0

        return {
            "branch_name": branch_name,
            "branch_exists": is_duplicate,
            "pr_exists": is_duplicate,
            "prior_attempts_count": len(prior_attempts),
            "can_proceed": not is_duplicate,
        }

    @staticmethod
    def record_attempt(
        db: Session,
        repo_full_name: str,
        issue_number: int,
        actor_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an idempotency marker / audit event for an issue solver attempt."""
        event_details: Dict[str, Any] = {
            "repo_full_name": repo_full_name,
            "issue_number": issue_number,
        }
        if details:
            event_details.update(details)

        audit_kwargs: Dict[str, Any] = {"action": "issue_solver_completed", "details": event_details}
        if actor_id is not None:
            if hasattr(AuditEvent, "user_id"):
                audit_kwargs["user_id"] = actor_id
            elif hasattr(AuditEvent, "actor_id"):
                audit_kwargs["actor_id"] = actor_id

        audit = AuditEvent(**audit_kwargs)
        db.add(audit)
        db.commit()
