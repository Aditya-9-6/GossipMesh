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


class MockStatusCode:
    ERROR = 2


class MockStatus:
    def __init__(self, status_code: int = 0, description: Optional[str] = None):
        self.status_code = status_code
        self.description = description


class MockEvent:
    def __init__(self, name: str):
        self.name = name


class MockSpan:
    def __init__(self, name: str, attributes: Optional[dict[str, Any]] = None):
        self.name = name
        self.attributes = attributes or {}
        self.status = MockStatus()
        self.events: list[MockEvent] = []

    def __enter__(self) -> MockSpan:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val:
            self.status = MockStatus(MockStatusCode.ERROR, str(exc_val))
            self.events.append(MockEvent("exception"))


class MockMemoryExporter:
    def __init__(self) -> None:
        self.spans: list[MockSpan] = []

    def clear(self) -> None:
        self.spans.clear()

    def get_finished_spans(self) -> list[MockSpan]:
        return self.spans


_exporter = MockMemoryExporter()


def get_memory_exporter() -> MockMemoryExporter:
    return _exporter


def setup_tracer_provider() -> None:
    pass


@contextmanager
def trace_span(name: str, attributes: Optional[dict[str, Any]] = None) -> Generator[MockSpan, None, None]:
    span = MockSpan(name, attributes)
    _exporter.spans.append(span)
    try:
        yield span
    except Exception as e:
        span.status = MockStatus(MockStatusCode.ERROR, str(e))
        span.events.append(MockEvent("exception"))
        raise


@contextmanager
def trace_api(endpoint: str, method: str) -> Generator[MockSpan, None, None]:
    with trace_span(f"API {method} {endpoint}") as span:
        yield span


@contextmanager
def trace_database(operation: str, table: str) -> Generator[MockSpan, None, None]:
    with trace_span(f"DB {operation} {table}") as span:
        yield span


@contextmanager
def trace_github(operation: str, repo: str) -> Generator[MockSpan, None, None]:
    with trace_span(f"GitHub {operation}", attributes={"repo": repo}) as span:
        yield span


@contextmanager
def trace_provider(provider: str, model: str) -> Generator[MockSpan, None, None]:
    with trace_span(f"LLM {provider}:{model}") as span:
        yield span


@contextmanager
def trace_queue(queue_name: str, task_id: str) -> Generator[MockSpan, None, None]:
    with trace_span(f"Queue {queue_name}") as span:
        yield span


@contextmanager
def trace_sandbox(command: str, timeout_s: float) -> Generator[MockSpan, None, None]:
    with trace_span("Sandbox Execute") as span:
        yield span


@contextmanager
def trace_webhook(source: str, event_type: str) -> Generator[MockSpan, None, None]:
    with trace_span(f"Webhook {source}:{event_type}") as span:
        yield span


@contextmanager
def trace_workflow(workflow_id: int, workflow_type: str) -> Generator[MockSpan, None, None]:
    with trace_span(f"Workflow {workflow_type}") as span:
        yield span
