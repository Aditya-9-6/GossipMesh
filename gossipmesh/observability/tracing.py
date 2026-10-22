"""
Distributed Tracing Engine using OpenTelemetry (Task 95).

Provides distributed trace spans across:
- API
- Webhooks
- Workflows
- Queues
- GitHub operations
- LLM Providers
- Database
- Sandbox execution

Strictly enforces that secrets, API keys, bearer tokens, and raw source code
are redacted and NEVER stored in trace attributes.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, StatusCode

from gossipmesh.core.config import settings
from gossipmesh.core.logging import redact_sensitive_data

# Global provider and tracer initialization
_RESOURCE = Resource.create(
    {
        "service.name": getattr(settings, "PROJECT_NAME", "gossipmesh"),
        "deployment.environment": getattr(settings, "ENVIRONMENT", "production"),
    }
)

_PROVIDER: Optional[TracerProvider] = None
_MEMORY_EXPORTER: Optional[InMemorySpanExporter] = None


def setup_tracer_provider(exporter: Optional[SpanExporter] = None) -> TracerProvider:
    """Configures global OpenTelemetry TracerProvider as a singleton."""
    global _PROVIDER, _MEMORY_EXPORTER
    if _PROVIDER is not None:
        return _PROVIDER

    _PROVIDER = TracerProvider(resource=_RESOURCE)

    if exporter:
        _PROVIDER.add_span_processor(SimpleSpanProcessor(exporter))
    else:
        _MEMORY_EXPORTER = InMemorySpanExporter()
        _PROVIDER.add_span_processor(SimpleSpanProcessor(_MEMORY_EXPORTER))

    trace.set_tracer_provider(_PROVIDER)
    return _PROVIDER


def get_memory_exporter() -> InMemorySpanExporter:
    """Returns active in-memory span exporter for verification."""
    global _MEMORY_EXPORTER
    if _MEMORY_EXPORTER is None:
        setup_tracer_provider()
    return _MEMORY_EXPORTER  # type: ignore


def get_tracer(name: str = "gossipmesh") -> trace.Tracer:
    """Returns tracer instance."""
    global _PROVIDER
    if _PROVIDER is None:
        setup_tracer_provider()
    return trace.get_tracer(name)


def sanitize_trace_attributes(attributes: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitizes attributes to ensure zero secrets or raw source code are recorded."""
    if not attributes:
        return {}

    sanitized: Dict[str, Any] = {}
    for key, val in attributes.items():
        if isinstance(val, (int, float, bool)):
            sanitized[key] = val
        elif isinstance(val, str):
            sanitized[key] = redact_sensitive_data(val)
        elif val is None:
            sanitized[key] = "null"
        else:
            sanitized[key] = redact_sensitive_data(str(val))
    return sanitized


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Span, None, None]:
    """Base context manager for tracing execution blocks with sanitized attributes."""
    tracer = get_tracer()
    clean_attrs = sanitize_trace_attributes(attributes)
    with tracer.start_as_current_span(name, attributes=clean_attrs) as span:
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(StatusCode.ERROR, description=str(e))
            raise


# -----------------------------------------------------------------------------
# Layer-Specific Tracing Helpers
# -----------------------------------------------------------------------------
@contextmanager
def trace_api(endpoint: str, method: str, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"http.route": endpoint, "http.method": method})
    with trace_span(f"API {method} {endpoint}", attributes=attrs) as span:
        yield span


@contextmanager
def trace_webhook(source: str, event_type: str, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"webhook.source": source, "webhook.event_type": event_type})
    with trace_span(f"Webhook {source}:{event_type}", attributes=attrs) as span:
        yield span


@contextmanager
def trace_workflow(workflow_id: str | int, workflow_type: str, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"workflow.id": str(workflow_id), "workflow.type": workflow_type})
    with trace_span(f"Workflow {workflow_type}", attributes=attrs) as span:
        yield span


@contextmanager
def trace_queue(queue_name: str, task_id: str, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"queue.name": queue_name, "queue.task_id": task_id})
    with trace_span(f"Queue {queue_name}", attributes=attrs) as span:
        yield span


@contextmanager
def trace_github(operation: str, repo: str, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"github.operation": operation, "github.repo": repo})
    with trace_span(f"GitHub {operation}", attributes=attrs) as span:
        yield span


@contextmanager
def trace_provider(provider: str, model: str, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"llm.provider": provider, "llm.model": model})
    with trace_span(f"LLM {provider}:{model}", attributes=attrs) as span:
        yield span


@contextmanager
def trace_database(operation: str, table: str, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"db.operation": operation, "db.table": table})
    with trace_span(f"DB {operation} {table}", attributes=attrs) as span:
        yield span


@contextmanager
def trace_sandbox(command: str, timeout_s: float, **attrs: Any) -> Generator[Span, None, None]:
    attrs.update({"sandbox.command": command, "sandbox.timeout_seconds": timeout_s})
    with trace_span("Sandbox Execute", attributes=attrs) as span:
        yield span
