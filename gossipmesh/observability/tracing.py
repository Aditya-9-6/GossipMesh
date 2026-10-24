"""Distributed tracing wrapper using OpenTelemetry with fallback support."""

from contextlib import contextmanager
from typing import Any, Dict, Iterator

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


class DummySpan:
    def __init__(self, name: str):
        self.name = name
        self.status = self
        self.status_code = 0
        self.description = ""
        self.attributes: Dict[str, Any] = {}
        self.events = []

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def record_exception(self, exception: Exception):
        self.events.append(exception)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.record_exception(exc_val)


class DummyExporter:
    def clear(self):
        pass

    def get_finished_spans(self):
        return []


_memory_exporter = DummyExporter()


def get_memory_exporter():
    if HAS_OTEL:
        global _memory_exporter
        return _memory_exporter
    return _memory_exporter


def setup_tracer_provider():
    if not HAS_OTEL:
        return
    global _memory_exporter
    provider = TracerProvider(resource=Resource.create({"service.name": "gossipmesh"}))
    _memory_exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(_memory_exporter))
    trace.set_tracer_provider(provider)


@contextmanager
def trace_span(name: str, attributes: Dict[str, Any] | None = None) -> Iterator[Any]:
    if not HAS_OTEL:
        span = DummySpan(name)
        if attributes:
            span.attributes.update(attributes)
        yield span
        return

    tracer = trace.get_tracer("gossipmesh")
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(StatusCode.ERROR, str(e))
            raise


@contextmanager
def trace_workflow(workflow_id: int, workflow_type: str):
    with trace_span(f"Workflow {workflow_type}", {"workflow_id": workflow_id, "workflow_type": workflow_type}) as s:
        yield s


@contextmanager
def trace_api(endpoint: str, method: str):
    with trace_span(f"API {method} {endpoint}", {"endpoint": endpoint, "method": method}) as s:
        yield s


@contextmanager
def trace_webhook(source: str, event_type: str):
    with trace_span(f"Webhook {source}:{event_type}", {"source": source, "event_type": event_type}) as s:
        yield s


@contextmanager
def trace_queue(queue_name: str, task_id: str):
    with trace_span(f"Queue {queue_name}", {"queue_name": queue_name, "task_id": task_id}) as s:
        yield s


@contextmanager
def trace_github(operation: str, repo: str):
    with trace_span(f"GitHub {operation}", {"operation": operation, "repo": repo}) as s:
        yield s


@contextmanager
def trace_provider(provider: str, model: str):
    with trace_span(f"LLM {provider}:{model}", {"provider": provider, "model": model}) as s:
        yield s


@contextmanager
def trace_database(operation: str, table: str):
    with trace_span(f"DB {operation} {table}", {"operation": operation, "table": table}) as s:
        yield s


@contextmanager
def trace_sandbox(command: str, timeout_s: float):
    with trace_span("Sandbox Execute", {"command": command, "timeout_s": timeout_s}) as s:
        yield s
