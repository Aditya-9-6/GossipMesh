"""
Prometheus Metrics collection and instrumentation for GossipMesh.
"""

import time
from typing import Any, Dict, Optional

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class MockMetric:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def labels(self, *args: Any, **kwargs: Any) -> "MockMetric":
            return self

        def inc(self, amount: float = 1.0, *args: Any, **kwargs: Any) -> None:
            pass

        def dec(self, amount: float = 1.0, *args: Any, **kwargs: Any) -> None:
            pass

        def set(self, value: float, *args: Any, **kwargs: Any) -> None:
            pass

        def observe(self, amount: float, *args: Any, **kwargs: Any) -> None:
            pass

    def Counter(*args: Any, **kwargs: Any) -> MockMetric:
        return MockMetric()

    def Gauge(*args: Any, **kwargs: Any) -> MockMetric:
        return MockMetric()

    def Histogram(*args: Any, **kwargs: Any) -> MockMetric:
        return MockMetric()

    def generate_latest(*args: Any, **kwargs: Any) -> bytes:
        return b"# Prometheus metrics mock\n"


# Define metrics
HTTP_REQUESTS_TOTAL = Counter(
    "gossipmesh_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "gossipmesh_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

HTTP_ERRORS_TOTAL = Counter(
    "gossipmesh_http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "status_code"],
)

WEBHOOK_EVENTS_TOTAL = Counter(
    "gossipmesh_webhook_events_total",
    "Total webhook events received",
    ["source", "event_type", "status"],
)

WORKFLOW_DURATION = Histogram(
    "gossipmesh_workflow_duration_seconds",
    "Workflow execution duration",
    ["workflow_type"],
)

QUEUE_DEPTH = Gauge(
    "gossipmesh_queue_depth",
    "Current queue depth",
    ["queue_name", "priority"],
)

JOB_RETRIES_TOTAL = Counter(
    "gossipmesh_job_retries_total",
    "Total background job retries",
    ["job_type", "reason"],
)

PROVIDER_REQUEST_DURATION = Histogram(
    "gossipmesh_provider_request_duration_seconds",
    "AI provider request duration",
    ["provider", "model"],
)

PROVIDER_FAILURES_TOTAL = Counter(
    "gossipmesh_provider_failures_total",
    "Total AI provider request failures",
    ["provider", "model", "error_type"],
)

AI_TOKENS_CONSUMED = Counter(
    "gossipmesh_ai_tokens_consumed_total",
    "Total AI tokens consumed",
    ["provider", "model", "token_type"],
)

REVIEW_FINDINGS_TOTAL = Counter(
    "gossipmesh_review_findings_total",
    "Total review findings detected",
    ["severity", "rule_category", "tenant_id"],
)

SANDBOX_FAILURES_TOTAL = Counter(
    "gossipmesh_sandbox_execution_failures_total",
    "Total sandbox execution failures",
    ["failure_reason", "exit_code"],
)

BILLING_USAGE_UNITS = Counter(
    "gossipmesh_billing_usage_units_total",
    "Total billing usage units recorded",
    ["metric_type", "tenant_id"],
)


def record_request(method: str, endpoint: str, status_code: int, duration_s: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration_s)
    if status_code >= 400:
        HTTP_ERRORS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()


def record_webhook(source: str, event_type: str, status: str) -> None:
    WEBHOOK_EVENTS_TOTAL.labels(source=source, event_type=event_type, status=status).inc()


def record_workflow(workflow_type: str, duration_s: float) -> None:
    WORKFLOW_DURATION.labels(workflow_type=workflow_type).observe(duration_s)


def set_queue_depth(queue_name: str, depth: float, priority: str = "normal") -> None:
    QUEUE_DEPTH.labels(queue_name=queue_name, priority=priority).set(depth)


def record_retry(job_type: str, reason: str) -> None:
    JOB_RETRIES_TOTAL.labels(job_type=job_type, reason=reason).inc()


def record_provider_call(
    provider: str, model: str, duration_s: float, is_error: bool = False, error_type: Optional[str] = None
) -> None:
    PROVIDER_REQUEST_DURATION.labels(provider=provider, model=model).observe(duration_s)
    if is_error:
        PROVIDER_FAILURES_TOTAL.labels(provider=provider, model=model, error_type=error_type or "unknown").inc()


def record_tokens(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    AI_TOKENS_CONSUMED.labels(provider=provider, model=model, token_type="prompt").inc(prompt_tokens)
    AI_TOKENS_CONSUMED.labels(provider=provider, model=model, token_type="completion").inc(completion_tokens)


def record_finding(severity: str, rule_category: str, tenant_id: str) -> None:
    REVIEW_FINDINGS_TOTAL.labels(severity=severity, rule_category=rule_category, tenant_id=tenant_id).inc()


def record_sandbox_failure(failure_reason: str, exit_code: int) -> None:
    SANDBOX_FAILURES_TOTAL.labels(failure_reason=failure_reason, exit_code=str(exit_code)).inc()


def record_billing_metric(metric_type: str, units: float, tenant_id: str) -> None:
    BILLING_USAGE_UNITS.labels(metric_type=metric_type, tenant_id=tenant_id).inc(units)


def generate_latest_metrics() -> bytes:
    return generate_latest()
