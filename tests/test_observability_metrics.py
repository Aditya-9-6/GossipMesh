import os
os.environ["TESTING"] = "true"

from fastapi.testclient import TestClient
from gossipmesh.api.main import app
from gossipmesh.observability.metrics import (
    CONTENT_TYPE_LATEST,
    generate_latest_metrics,
    record_billing_metric,
    record_finding,
    record_provider_call,
    record_request,
    record_retry,
    record_sandbox_failure,
    record_tokens,
    record_webhook,
    record_workflow,
    set_queue_depth,
)


def test_record_all_thirteen_metric_dimensions():
    # 1. HTTP Request & Latency & Error
    record_request(method="GET", endpoint="/api/v1/projects", status_code=200, duration_s=0.045)
    record_request(method="POST", endpoint="/api/v1/auth/login", status_code=401, duration_s=0.120)

    # 2. Webhook
    record_webhook(source="github", event_type="pull_request.opened", status="success")

    # 3. Workflow duration
    record_workflow(workflow_type="autonomous_ci_review", duration_s=14.2)

    # 4. Queue depth
    set_queue_depth(queue_name="high_priority", depth=8.0, priority="urgent")

    # 5. Job retries
    record_retry(job_type="review_job", reason="provider_rate_limit")

    # 6. Provider calls & failures
    record_provider_call(provider="gemini", model="gemini-1.5-pro", duration_s=1.85)
    record_provider_call(provider="openai", model="gpt-4o", duration_s=0.6, is_error=True, error_type="HTTP_429")

    # 7. Tokens
    record_tokens(provider="gemini", model="gemini-1.5-pro", prompt_tokens=1500, completion_tokens=350)

    # 8. Review findings
    record_finding(severity="HIGH", rule_category="sql_injection", tenant_id="tenant_1")

    # 9. Sandbox failure
    record_sandbox_failure(failure_reason="OOMKilled", exit_code=137)

    # 10. Billing usage
    record_billing_metric(metric_type="reviewed_prs", units=1.0, tenant_id="tenant_1")

    # Render metrics payload
    raw_metrics = generate_latest_metrics().decode("utf-8")

    assert "gossipmesh_http_requests_total" in raw_metrics
    assert "gossipmesh_http_request_duration_seconds" in raw_metrics
    assert "gossipmesh_http_errors_total" in raw_metrics
    assert "gossipmesh_webhook_events_total" in raw_metrics
    assert "gossipmesh_workflow_duration_seconds" in raw_metrics
    assert "gossipmesh_queue_depth" in raw_metrics
    assert "gossipmesh_job_retries_total" in raw_metrics
    assert "gossipmesh_provider_request_duration_seconds" in raw_metrics
    assert "gossipmesh_provider_failures_total" in raw_metrics
    assert "gossipmesh_ai_tokens_consumed_total" in raw_metrics
    assert "gossipmesh_review_findings_total" in raw_metrics
    assert "gossipmesh_sandbox_execution_failures_total" in raw_metrics
    assert "gossipmesh_billing_usage_units_total" in raw_metrics


def test_metrics_api_endpoint():
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert CONTENT_TYPE_LATEST in response.headers.get("content-type", "")
    assert "gossipmesh_http_requests_total" in response.text
