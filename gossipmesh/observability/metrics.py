import os
from typing import Any

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _DummyMetric:
        def labels(self, *args: Any, **kwargs: Any) -> "_DummyMetric":
            return self

        def inc(self, amount: float = 1.0, *args: Any, **kwargs: Any) -> None:
            pass

        def observe(self, amount: float, *args: Any, **kwargs: Any) -> None:
            pass

        def set(self, value: float, *args: Any, **kwargs: Any) -> None:
            pass

    def Counter(*args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()

    def Histogram(*args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()

    def Gauge(*args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()

    def generate_latest(*args: Any, **kwargs: Any) -> bytes:
        return b"# prometheus_client not installed\n"


# Define standard metrics
REQUEST_COUNT = Counter("gossipmesh_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"])
REQUEST_LATENCY = Histogram("gossipmesh_http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])
REQUEST_ERRORS = Counter("gossipmesh_http_errors_total", "Total HTTP errors", ["method", "endpoint", "status_code"])
WEBHOOK_COUNT = Counter("gossipmesh_webhook_events_total", "Total webhook events", ["source", "event_type", "status"])
WORKFLOW_DURATION = Histogram("gossipmesh_workflow_duration_seconds", "Workflow execution duration", ["workflow_type"])
QUEUE_DEPTH = Gauge("gossipmesh_queue_depth", "Queue depth", ["queue_name", "priority"])
JOB_RETRIES = Counter("gossipmesh_job_retries_total", "Total job retries", ["job_type", "reason"])
PROVIDER_LATENCY = Histogram(
    "gossipmesh_provider_request_duration_seconds", "AI provider request latency", ["provider", "model"]
)
PROVIDER_FAILURES = Counter(
    "gossipmesh_provider_failures_total", "Total AI provider failures", ["provider", "model", "error_type"]
)
AI_TOKENS = Counter(
    "gossipmesh_ai_tokens_consumed_total", "Total AI tokens consumed", ["provider", "model", "token_type"]
)
REVIEW_FINDINGS = Counter(
    "gossipmesh_review_findings_total", "Total review findings", ["severity", "rule_category", "tenant_id"]
)
SANDBOX_FAILURES = Counter(
    "gossipmesh_sandbox_execution_failures_total", "Total sandbox execution failures", ["failure_reason", "exit_code"]
)
BILLING_USAGE = Counter(
    "gossipmesh_billing_usage_units_total", "Total billing usage units", ["metric_type", "tenant_id"]
)


def record_request(method: str, endpoint: str, status_code: int, duration_s: float) -> None:
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration_s)
    if status_code >= 400:
        REQUEST_ERRORS.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()


def record_webhook(source: str, event_type: str, status: str) -> None:
    WEBHOOK_COUNT.labels(source=source, event_type=event_type, status=status).inc()


def record_workflow(workflow_type: str, duration_s: float) -> None:
    WORKFLOW_DURATION.labels(workflow_type=workflow_type).observe(duration_s)


def set_queue_depth(queue_name: str, depth: float, priority: str = "normal") -> None:
    QUEUE_DEPTH.labels(queue_name=queue_name, priority=priority).set(depth)


def record_retry(job_type: str, reason: str) -> None:
    JOB_RETRIES.labels(job_type=job_type, reason=reason).inc()


def record_provider_call(
    provider: str, model: str, duration_s: float, is_error: bool = False, error_type: str = ""
) -> None:
    PROVIDER_LATENCY.labels(provider=provider, model=model).observe(duration_s)
    if is_error:
        PROVIDER_FAILURES.labels(provider=provider, model=model, error_type=error_type or "UNKNOWN").inc()


def record_tokens(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    AI_TOKENS.labels(provider=provider, model=model, token_type="prompt").inc(float(prompt_tokens))
    AI_TOKENS.labels(provider=provider, model=model, token_type="completion").inc(float(completion_tokens))


def record_finding(severity: str, rule_category: str, tenant_id: str) -> None:
    REVIEW_FINDINGS.labels(severity=severity, rule_category=rule_category, tenant_id=tenant_id).inc()


def record_sandbox_failure(failure_reason: str, exit_code: int) -> None:
    SANDBOX_FAILURES.labels(failure_reason=failure_reason, exit_code=str(exit_code)).inc()


def record_billing_metric(metric_type: str, units: int | float, tenant_id: str) -> None:
    BILLING_USAGE.labels(metric_type=metric_type, tenant_id=tenant_id).inc(float(units))


def generate_latest_metrics() -> bytes:
    return generate_latest()
