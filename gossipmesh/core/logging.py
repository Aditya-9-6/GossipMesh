import logging
import json
import re
import sys
import contextvars
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Optional

from gossipmesh.core.config import settings

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
workflow_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("workflow_id", default=None)
job_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("job_id", default=None)
organization_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("organization_id", default=None)

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

CODE_BLOCK_PATTERN = re.compile(r"(```[\s\S]*?```|(?:def\s+[a-zA-Z_]\w*\s*\(|class\s+[a-zA-Z_]\w*[:\(])[\s\S]{40,})")


def scrub_sensitive_data(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        if "bearer" in pattern.pattern.lower():
            text = pattern.sub(r"\1[REDACTED_TOKEN]", text)
        elif "password" in pattern.pattern.lower() or "secret" in pattern.pattern.lower():
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED_SECRET]", text)
    text = CODE_BLOCK_PATTERN.sub("[REDACTED_SOURCE_CODE]", text)
    return text


redact_sensitive_data = scrub_sensitive_data


class StructuredJSONFormatter(logging.Formatter):
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
            "service": getattr(settings, "PROJECT_NAME", "gossipmesh"),
        }

        if req_id:
            log_payload["correlation_id"] = req_id

        for k, v in record.__dict__.items():
            if k not in [
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "id",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ]:
                log_payload[k] = v

        if record.exc_info:
            log_payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


JSONFormatter = StructuredJSONFormatter


@contextmanager
def bind_logging_context(
    request_id: Optional[str] = None,
    workflow_id: Optional[Any] = None,
    job_id: Optional[Any] = None,
    organization_id: Optional[Any] = None,
) -> Generator[None, None, None]:
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
        for var, token in tokens:
            var.reset(token)


def log_structured_event(logger: logging.Logger, level: int, event: str, message: str, **kwargs: Any) -> None:
    logger.log(level, message, extra={"event": event, **kwargs})


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(handler)
