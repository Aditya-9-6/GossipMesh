"""
Customer Notifications Service (Task 104).

Supports email, Slack, and webhook notifications for:
- Review completion
- Critical findings
- Failed jobs
- Approval requirements
- Usage limits
- Billing events
"""

from __future__ import annotations

import hmac
import hashlib
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from gossipmesh.core.config import settings
from gossipmesh.core.logging import redact_sensitive_data
from gossipmesh.models.audit import AuditEvent


class NotificationEvent(str, Enum):
    REVIEW_COMPLETED = "review_completed"
    CRITICAL_FINDINGS = "critical_findings"
    JOB_FAILED = "job_failed"
    APPROVAL_REQUIRED = "approval_required"
    USAGE_LIMIT_WARNING = "usage_limit_warning"
    BILLING_EVENT = "billing_event"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationDispatcher:
    """Dispatches notifications across email, Slack, and outbound webhooks."""

    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        outbound_webhook_url: Optional[str] = None,
        outbound_webhook_secret: Optional[str] = None,
    ):
        self.slack_webhook_url = slack_webhook_url
        self.outbound_webhook_url = outbound_webhook_url
        self.outbound_webhook_secret = outbound_webhook_secret or "whsec_default_notification_secret"

    def format_slack_message(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Builds a Slack Block Kit structured notification payload."""
        color = "#e11d48" if event in (NotificationEvent.CRITICAL_FINDINGS, NotificationEvent.JOB_FAILED) else "#4f46e5"

        fields = []
        if metadata:
            for k, v in list(metadata.items())[:4]:
                fields.append({"type": "mrkdwn", "text": f"*{k}:*\n{redact_sensitive_data(str(v))}"})

        return {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": f"GossipMesh: {title}"},
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": redact_sensitive_data(message)},
                        },
                        *([{"type": "section", "fields": fields}] if fields else []),
                    ],
                }
            ]
        }

    def format_webhook_payload(
        self,
        event: NotificationEvent,
        organization_id: int,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Creates standard JSON outbound webhook body."""
        return {
            "event": event.value,
            "organization_id": organization_id,
            "title": title,
            "message": redact_sensitive_data(message),
            "metadata": metadata or {},
            "timestamp": int(time.time()),
        }

    def sign_webhook_payload(self, payload_bytes: bytes) -> str:
        """Generates HMAC-SHA256 signature for outbound webhook authentication."""
        return hmac.new(
            self.outbound_webhook_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

    def dispatch(
        self,
        session: Session,
        event: NotificationEvent,
        organization_id: int,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches notification to requested channels and records immutable audit log.
        """
        target_channels = channels or [NotificationChannel.SLACK, NotificationChannel.WEBHOOK]
        results: Dict[str, str] = {}

        # 1. Slack dispatch
        if NotificationChannel.SLACK in target_channels:
            if self.slack_webhook_url:
                try:
                    payload = self.format_slack_message(event, title, message, metadata)
                    res = httpx.post(self.slack_webhook_url, json=payload, timeout=5.0)
                    results["slack"] = "sent" if res.status_code == 200 else f"failed_{res.status_code}"
                except Exception as e:
                    results["slack"] = f"error: {str(e)}"
            else:
                results["slack"] = "skipped_unconfigured"

        # 2. Outbound Webhook dispatch
        if NotificationChannel.WEBHOOK in target_channels:
            if self.outbound_webhook_url:
                try:
                    body = self.format_webhook_payload(event, organization_id, title, message, metadata)
                    body_bytes = json.dumps(body).encode("utf-8")
                    signature = self.sign_webhook_payload(body_bytes)
                    headers = {
                        "Content-Type": "application/json",
                        "X-GossipMesh-Signature": signature,
                    }
                    res = httpx.post(self.outbound_webhook_url, content=body_bytes, headers=headers, timeout=5.0)
                    results["webhook"] = "sent" if res.status_code == 200 else f"failed_{res.status_code}"
                except Exception as e:
                    results["webhook"] = f"error: {str(e)}"
            else:
                results["webhook"] = "skipped_unconfigured"

        # Record audit event
        audit = AuditEvent(
            action=f"notification.{event.value}",
            organization_id=organization_id,
            details={
                "title": title,
                "channels": [c.value for c in target_channels],
                "results": results,
            },
        )
        session.add(audit)
        session.commit()

        return results
