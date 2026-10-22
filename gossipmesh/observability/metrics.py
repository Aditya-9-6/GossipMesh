"""
Prometheus Metrics Engine for GossipMesh Enterprise (Task 94).

Tracks:
- Requests, Latency, Errors
- Webhooks
- Workflow duration & queue depth
- Job retries
- Provider latency & failures
- AI Token consumption
- PR review findings
- Sandbox failures
- Billing usage
"""

from __future__ import annotations

import time
from typing import Optional
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Dedicated registry to isolate application metrics
REGISTRY = CollectorRegistry(auto_describe=True)

# 1. HTTP Traffic & Errors
HTTP_REQUESTS_TOTAL = Counter(
    "gossipmesh_http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "gossipmesh_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

HTTP_ERRORS_TOTAL = Counter(
    "gossipmesh_http_errors_total",
    "Total HTTP errors categorized by error type",
    ["method", "endpoint", "error_type"],
    registry=REGISTRY,
)

# 2. Webhook Ingestion
WEBHOOK_EVENTS_TOTAL = Counter(
    "gossipmesh_webhook_events_total",
    "Total inbound webhook events processed",
    ["source", "event_type", "status"],
    registry=REGISTRY,
)

# 3. Workflows & Queue Depth
WORKFLOW_DURATION_SECONDS = Histogram(
    "gossipmesh_workflow_duration_seconds",
    "End-to-end autonomous workflow duration in seconds",
    ["workflow_type"],
    buckets=[1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0],
    registry=REGISTRY,
)

QUEUE_DEPTH = Gauge(
    "gossipmesh_queue_depth",
    "Current pending tasks waiting in task execution queues",
    ["queue_name", "priority"],
    registry=REGISTRY,
)

JOB_RETRIES_TOTAL = Counter(
    "gossipmesh_job_retries_total",
    "Total background job retry attempts",
    ["job_type", "reason"],
    registry=REGISTRY,
)

# 4. LLM Providers
PROVIDER_LATENCY_SECONDS = Histogram(
    "gossipmesh_provider_request_duration_seconds",
    "Upstream AI provider call latency in seconds",
    ["provider", "model"],
    buckets=[0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0],
    registry=REGISTRY,
)

PROVIDER_FAILURES_TOTAL = Counter(
    "gossipmesh_provider_failures_total",
    "Total failed provider calls by error category",
    ["provider", "model", "error_type"],
    registry=REGISTRY,
)

AI_TOKENS_CONSUMED_TOTAL = Counter(
    "gossipmesh_ai_tokens_consumed_total",
    "Total AI tokens consumed across prompt and completion",
    ["provider", "model", "token_type"],
    registry=REGISTRY,
)

# 5. Review Findings
REVIEW_FINDINGS_TOTAL = Counter(
    "gossipmesh_review_findings_total",
    "Total code review findings produced",
    ["severity", "rule_category", "tenant_id"],
    registry=REGISTRY,
)

# 6. Sandbox Execution
SANDBOX_FAILURES_TOTAL = Counter(
    "gossipmesh_sandbox_execution_failures_total",
    "Total isolated sandbox failures by failure reason",
    ["failure_reason", "exit_code"],
    registry=REGISTRY,
)

# 7. Billing Usage
BILLING_USAGE_UNITS_TOTAL = Counter(
    "gossipmesh_billing_usage_units_total",
    "Total metered billing usage consumed",
    ["metric_type", "tenant_id"],
    registry=REGISTRY,
)


def record_request(method: str, endpoint: str, status_code: int, duration_s: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration_s)
    if status_code >= 400:
        error_type = f"{status_code}_error"
        HTTP_ERRORS_TOTAL.labels(method=method, endpoint=endpoint, error_type=error_type).inc()


def record_webhook(source: str, event_type: str, status: str = "success") -> None:
    WEBHOOK_EVENTS_TOTAL.labels(source=source, event_type=event_type, status=status).inc()


def record_workflow(workflow_type: str, duration_s: float) -> None:
    WORKFLOW_DURATION_SECONDS.labels(workflow_type=workflow_type).observe(duration_s)


def set_queue_depth(queue_name: str, depth: float, priority: str = "default") -> None:
    QUEUE_DEPTH.labels(queue_name=queue_name, priority=priority).set(depth)


def record_retry(job_type: str, reason: str) -> None:
    JOB_RETRIES_TOTAL.labels(job_type=job_type, reason=reason).inc()


def record_provider_call(
    provider: str,
    model: str,
    duration_s: float,
    is_error: bool = False,
    error_type: Optional[str] = None,
) -> None:
    PROVIDER_LATENCY_SECONDS.labels(provider=provider, model=model).observe(duration_s)
    if is_error:
        err = error_type or "unknown_error"
        PROVIDER_FAILURES_TOTAL.labels(provider=provider, model=model, error_type=err).inc()


def record_tokens(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    if prompt_tokens > 0:
        AI_TOKENS_CONSUMED_TOTAL.labels(provider=provider, model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens > 0:
        AI_TOKENS_CONSUMED_TOTAL.labels(provider=provider, model=model, token_type="completion").inc(completion_tokens)


def record_finding(severity: str, rule_category: str, tenant_id: str = "default") -> None:
    REVIEW_FINDINGS_TOTAL.labels(severity=severity, rule_category=rule_category, tenant_id=str(tenant_id)).inc()


def record_sandbox_failure(failure_reason: str, exit_code: int = 1) -> None:
    SANDBOX_FAILURES_TOTAL.labels(failure_reason=failure_reason, exit_code=str(exit_code)).inc()


def record_billing_metric(metric_type: str, units: float = 1.0, tenant_id: str = "default") -> None:
    BILLING_USAGE_UNITS_TOTAL.labels(metric_type=metric_type, tenant_id=str(tenant_id)).inc(units)


def generate_latest_metrics() -> bytes:
    """Returns the Prometheus formatted metrics payload."""
    return generate_latest(REGISTRY)
