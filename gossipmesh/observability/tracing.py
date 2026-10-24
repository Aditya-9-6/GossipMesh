"""
Distributed Tracing module for GossipMesh (OpenTelemetry wrapper).
"""

from __future__ import annotations

import contextlib
import logging
import os
from typing import Any, Dict, Generator, Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import StatusCode

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False
    trace = None
    Resource = None
    TracerProvider = None
    SimpleSpanProcessor = None
    InMemorySpanExporter = None
    StatusCode = None

# Global provider and tracer initialization
if Resource is not None:
    try:
        _RESOURCE = Resource.create(
            {
                "service.name": getattr(settings, "PROJECT_NAME", "gossipmesh"),
                "deployment.environment": getattr(settings, "ENVIRONMENT", "production"),
            }
        )
    except NameError:
        _RESOURCE = Resource.create(
            {
                "service.name": "gossipmesh",
                "deployment.environment": "production",
            }
        )
else:
    _RESOURCE = None

logger = logging.getLogger(__name__)

_tracer_provider: Any = None
_memory_exporter: Any = None
_MEMORY_EXPORTER: Any = None


class DummySpan:
    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = redact_attributes(attributes or {})
        self.status = type("DummyStatus", (), {"status_code": 0, "description": ""})()
        self.events: list[Any] = []

    def __enter__(self) -> DummySpan:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val:
            self.status.status_code = 2
            self.status.description = str(exc_val)
            self.events.append(type("DummyEvent", (), {"name": "exception"})())

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = redact_value(key, value)

    def record_exception(self, exception: Exception) -> None:
        self.status.status_code = 2
        self.status.description = str(exception)
        self.events.append(type("DummyEvent", (), {"name": "exception"})())


class DummyMemoryExporter:
    def __init__(self) -> None:
        self.spans: list[Any] = []

    def clear(self) -> None:
        self.spans.clear()

    def get_finished_spans(self) -> list[Any]:
        return self.spans


def redact_value(key: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value
    lower_key = key.lower()
    if any(secret in lower_key for secret in ["api_key", "token", "secret", "password", "auth_header"]):
        if "token" in lower_key or "auth" in lower_key:
            return "[REDACTED_TOKEN]"
        return "[REDACTED_SECRET]"
    if "source" in lower_key or "def " in value or "class " in value:
        return "[REDACTED_SOURCE_CODE]"
    return value


def redact_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    return {k: redact_value(k, v) for k, v in attributes.items()}


def setup_tracer_provider() -> Any:
    global _tracer_provider, _memory_exporter, _MEMORY_EXPORTER
    if not HAS_OTEL:
        _memory_exporter = DummyMemoryExporter()
        _MEMORY_EXPORTER = _memory_exporter
        return None
    if _tracer_provider is None:
        resource = _RESOURCE or Resource.create({"service.name": "gossipmesh"})
        _tracer_provider = TracerProvider(resource=resource)
        _memory_exporter = InMemorySpanExporter()
        _MEMORY_EXPORTER = _memory_exporter
        processor = SimpleSpanProcessor(_memory_exporter)
        _tracer_provider.add_span_processor(processor)
        trace.set_tracer_provider(_tracer_provider)
    return _tracer_provider


def get_memory_exporter() -> Any:
    """Returns active in-memory span exporter for verification."""
    global _memory_exporter, _MEMORY_EXPORTER
    if _tracer_provider is None:
        setup_tracer_provider()
    return _memory_exporter or _MEMORY_EXPORTER


@contextlib.contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[Any, None, None]:
    if not HAS_OTEL:
        span = DummySpan(name, attributes)
        yield span
        exporter = get_memory_exporter()
        if exporter and hasattr(exporter, "spans"):
            exporter.spans.append(span)
        return

    provider = setup_tracer_provider()
    tracer = provider.get_tracer("gossipmesh")
    redacted_attrs = redact_attributes(attributes or {})
    with tracer.start_as_current_span(name, attributes=redacted_attrs) as span:
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(StatusCode.ERROR, str(e))
            raise


@contextlib.contextmanager
def trace_workflow(workflow_id: Any, workflow_type: str) -> Generator[Any, None, None]:
    with trace_span(f"Workflow {workflow_type}", {"workflow.id": workflow_id, "workflow.type": workflow_type}) as span:
        yield span


@contextlib.contextmanager
def trace_api(endpoint: str, method: str) -> Generator[Any, None, None]:
    with trace_span(f"API {method} {endpoint}", {"http.endpoint": endpoint, "http.method": method}) as span:
        yield span


@contextlib.contextmanager
def trace_webhook(source: str, event_type: str) -> Generator[Any, None, None]:
    with trace_span(f"Webhook {source}:{event_type}", {"webhook.source": source, "webhook.event": event_type}) as span:
        yield span


@contextlib.contextmanager
def trace_queue(queue_name: str, task_id: str) -> Generator[Any, None, None]:
    with trace_span(f"Queue {queue_name}", {"queue.name": queue_name, "queue.task_id": task_id}) as span:
        yield span


@contextlib.contextmanager
def trace_github(operation: str, repo: str) -> Generator[Any, None, None]:
    with trace_span(f"GitHub {operation}", {"github.operation": operation, "github.repo": repo}) as span:
        yield span


@contextlib.contextmanager
def trace_provider(provider: str, model: str) -> Generator[Any, None, None]:
    with trace_span(f"LLM {provider}:{model}", {"llm.provider": provider, "llm.model": model}) as span:
        yield span


@contextlib.contextmanager
def trace_database(operation: str, table: str) -> Generator[Any, None, None]:
    with trace_span(f"DB {operation} {table}", {"db.operation": operation, "db.table": table}) as span:
        yield span


@contextlib.contextmanager
def trace_sandbox(command: str, timeout_s: float) -> Generator[Any, None, None]:
    with trace_span("Sandbox Execute", {"sandbox.command": command, "sandbox.timeout": timeout_s}) as span:
        yield span
