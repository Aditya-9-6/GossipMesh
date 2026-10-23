import logging
import json
import re
import sys
import contextvars
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
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)([^\"',}]+)", re.IGNORECASE),
    re.compile(r"(client_secret[\"']?\s*[:=]\s*[\"']?)([^\"',}]+)", re.IGNORECASE),
    re.compile(r"(-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----)"),
]

# Source code block detector pattern
CODE_BLOCK_PATTERN = re.compile(r"(```[\s\S]*?```|(?:def\s+[a-zA-Z_]\w*\s*\(|class\s+[a-zA-Z_]\w*[:\(])[\s\S]{40,})")


def scrub_sensitive_data(text: str) -> str:
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


class JSONFormatter(logging.Formatter):
    def format(self, record):
        from gossipmesh.middleware.correlation import get_correlation_id

        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": scrub_sensitive_data(record.getMessage()),
            "logger": record.name,
        }

        try:
            req_id = get_correlation_id()
            if req_id:
                log_data["correlation_id"] = req_id
        except LookupError:
            pass

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as structured, machine-parseable, secret-scrubbed JSON."""

    def format(self, record: logging.LogRecord) -> str:
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
            "message": scrub_sensitive_data(record.getMessage()),
            "logger": record.name,
        }

        if req_id:
            log_payload["correlation_id"] = req_id

        if record.exc_info:
            log_payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(handler)
