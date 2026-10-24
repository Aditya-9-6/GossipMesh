from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import StatusCode

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None
    Resource = None
    TracerProvider = None
    SimpleSpanProcessor = None
    InMemorySpanExporter = None

    class StatusCode:
        OK = 0
        ERROR = 2


_memory_exporter = None
_tracer_provider = None


def setup_tracer_provider() -> Any:
    global _memory_exporter, _tracer_provider
    if not OPENTELEMETRY_AVAILABLE:
        return None
    if _tracer_provider is None:
        _tracer_provider = TracerProvider(resource=Resource.create({"service.name": "gossipmesh"}))
        _memory_exporter = InMemorySpanExporter()
        _tracer_provider.add_span_processor(SimpleSpanProcessor(_memory_exporter))
        trace.set_tracer_provider(_tracer_provider)
    return _tracer_provider


def get_memory_exporter() -> Any:
    global _memory_exporter
    if _memory_exporter is None:
        setup_tracer_provider()
    return _memory_exporter


@contextmanager
def trace_span(name: str, attributes: Dict[str, Any] | None = None, **kwargs: Any) -> Generator[Any, None, None]:
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return
    setup_tracer_provider()
    tracer = trace.get_tracer("gossipmesh")
    redacted_attrs = _redact_attributes(attributes or {})
    with tracer.start_as_current_span(name, attributes=redacted_attrs, **kwargs) as span:
        try:
            yield span
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise


def _redact_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    redacted = {}
    secret_keys = {"api_key", "github_token", "webhook_secret", "auth_header", "source_dump"}
    for k, v in attributes.items():
        if any(sk in k.lower() for sk in secret_keys):
            if "token" in k.lower():
                redacted[k] = "[REDACTED_TOKEN]"
            elif "source" in k.lower():
                redacted[k] = "[REDACTED_SOURCE_CODE]"
            else:
                redacted[k] = "[REDACTED_SECRET]"
        else:
            redacted[k] = v
    return redacted


@contextmanager
def trace_workflow(workflow_id: int | str, workflow_type: str) -> Generator[Any, None, None]:
    with trace_span(f"Workflow {workflow_type}", {"workflow.id": workflow_id, "workflow.type": workflow_type}) as span:
        yield span


@contextmanager
def trace_api(endpoint: str, method: str) -> Generator[Any, None, None]:
    with trace_span(f"API {method} {endpoint}", {"http.method": method, "http.endpoint": endpoint}) as span:
        yield span


@contextmanager
def trace_webhook(source: str, event_type: str) -> Generator[Any, None, None]:
    with trace_span(f"Webhook {source}:{event_type}", {"webhook.source": source, "webhook.event": event_type}) as span:
        yield span


@contextmanager
def trace_queue(queue_name: str, task_id: str) -> Generator[Any, None, None]:
    with trace_span(f"Queue {queue_name}", {"queue.name": queue_name, "queue.task_id": task_id}) as span:
        yield span


@contextmanager
def trace_github(operation: str, repo: str) -> Generator[Any, None, None]:
    with trace_span(f"GitHub {operation}", {"github.operation": operation, "github.repo": repo}) as span:
        yield span


@contextmanager
def trace_provider(provider: str, model: str) -> Generator[Any, None, None]:
    with trace_span(f"LLM {provider}:{model}", {"llm.provider": provider, "llm.model": model}) as span:
        yield span


@contextmanager
def trace_database(operation: str, table: str) -> Generator[Any, None, None]:
    with trace_span(f"DB {operation} {table}", {"db.operation": operation, "db.table": table}) as span:
        yield span


@contextmanager
def trace_sandbox(command: str, timeout_s: float) -> Generator[Any, None, None]:
    with trace_span("Sandbox Execute", {"sandbox.command": command, "sandbox.timeout": timeout_s}) as span:
        yield span
