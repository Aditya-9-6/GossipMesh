"""
Production Structured Logging & Secret Redaction (Task 93).

Emits structured JSON logs containing service, environment, request ID,
workflow ID, job ID, organization ID, event, duration, and error category,
while strictly redacting API keys, bearer tokens, credentials, and raw source code.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Optional

from gossipmesh.core.config import settings

# Context Variables for Distributed Observability Context
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
workflow_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("workflow_id", default=None)
job_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("job_id", default=None)
organization_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("organization_id", default=None)

# Secret and credential regex patterns
SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9_-]{20,})", re.IGNORECASE),
    re.compile(r"(ghp_[a-zA-Z0-9]{36,})", re.IGNORECASE),
    re.compile(r"(github_pat_[a-zA-Z0-9_]{36,})", re.IGNORECASE),
    re.compile(r"(whsec_[a-zA-Z0-9]{20,})", re.IGNORECASE),
    re.compile(r"(bearer\s+)([a-zA-Z0-9\._-]{20,})", re.IGNORECASE),
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)([^\s\"',}]+)", re.IGNORECASE),
    re.compile(r"(client_secret[\"']?\s*[:=]\s*[\"']?)([^\s\"',}]+)", re.IGNORECASE),
    re.compile(r"(-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----)"),
]

# Source code block detector pattern
CODE_BLOCK_PATTERN = re.compile(
    r"(```[\s\S]*?```|(?:def\s+[a-zA-Z_]\w*\s*\(|class\s+[a-zA-Z_]\w*[:\(])[\s\S]{40,})"
)


def redact_sensitive_data(text: str) -> str:
    """Masks credentials, private tokens, passwords, and raw source code blocks."""
    if not isinstance(text, str):
        text = str(text)

    # 1. Redact credentials
    for pattern in SECRET_PATTERNS:
        if "bearer" in pattern.pattern.lower():
            text = pattern.sub(r"\1[REDACTED_TOKEN]", text)
        elif "password" in pattern.pattern.lower() or "secret" in pattern.pattern.lower():
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED_SECRET]", text)

    # 2. Redact large raw source code dumps
    text = CODE_BLOCK_PATTERN.sub("[REDACTED_SOURCE_CODE]", text)

    return text


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as structured, machine-parseable, secret-scrubbed JSON."""

    def format(self, record: logging.LogRecord) -> str:
        # Retrieve correlation ID from middleware if available
        req_id = request_id_var.get()
        if not req_id:
            try:
                from gossipmesh.middleware.correlation import get_correlation_id
                req_id = get_correlation_id()
            except Exception:
                req_id = None

        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(settings, "PROJECT_NAME", "gossipmesh"),
            "environment": getattr(settings, "ENVIRONMENT", "production"),
            "logger": record.name,
            "message": redact_sensitive_data(record.getMessage()),
        }

        # Structured context coordinates
        if req_id:
            log_payload["request_id"] = req_id
        wf_id = workflow_id_var.get() or getattr(record, "workflow_id", None)
        if wf_id is not None:
            log_payload["workflow_id"] = str(wf_id)
        j_id = job_id_var.get() or getattr(record, "job_id", None)
        if j_id is not None:
            log_payload["job_id"] = str(j_id)
        org_id = organization_id_var.get() or getattr(record, "organization_id", None)
        if org_id is not None:
            log_payload["organization_id"] = str(org_id)

        # Operational attributes
        event = getattr(record, "event", None)
        if event:
            log_payload["event"] = str(event)
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log_payload["duration_ms"] = float(duration_ms)
        error_category = getattr(record, "error_category", None)
        if error_category:
            log_payload["error_category"] = str(error_category)

        # Tracebacks
        if record.exc_info:
            formatted_exc = self.formatException(record.exc_info)
            log_payload["exc_info"] = redact_sensitive_data(formatted_exc)

        return json.dumps(log_payload)


# Backwards compatibility alias
JSONFormatter = StructuredJSONFormatter


@contextmanager
def bind_logging_context(
    request_id: Optional[str] = None,
    workflow_id: Optional[str | int] = None,
    job_id: Optional[str | int] = None,
    organization_id: Optional[str | int] = None,
) -> Generator[None, None, None]:
    """Context manager for binding execution metadata to structured logs."""
    tokens = []
    if request_id is not None:
        tokens.append((request_id_var, request_id_var.set(str(request_id))))
    if workflow_id is not None:
        tokens.append((workflow_id_var, workflow_id_var.set(str(workflow_id))))
    if job_id is not None:
        tokens.append((job_id_var, job_id_var.set(str(job_id))))
    if organization_id is not None:
        tokens.append((organization_id_var, organization_id_var.set(str(organization_id))))

    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


def log_structured_event(
    logger: logging.Logger,
    level: int,
    event: str,
    message: str,
    duration_ms: Optional[float] = None,
    error_category: Optional[str] = None,
    **extra: Any,
) -> None:
    """Emits an event-centric structured log record."""
    extra_data = {
        "event": event,
        "duration_ms": duration_ms,
        "error_category": error_category,
        **extra,
    }
    logger.log(level, message, extra=extra_data)


def setup_logging(level: int = logging.INFO) -> None:
    """Configures root logger with the StructuredJSONFormatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(handler)
