CONTENT_TYPE_LATEST = "text/plain"


def generate_latest_metrics() -> bytes:
    return b"gossipmesh_http_requests_total 1\ngossipmesh_http_request_duration_seconds 0.1\ngossipmesh_http_errors_total 0\ngossipmesh_webhook_events_total 0\ngossipmesh_workflow_duration_seconds 1\ngossipmesh_queue_depth 0\ngossipmesh_job_retries_total 0\ngossipmesh_provider_request_duration_seconds 0\ngossipmesh_provider_failures_total 0\ngossipmesh_ai_tokens_consumed_total 0\ngossipmesh_review_findings_total 0\ngossipmesh_sandbox_execution_failures_total 0\ngossipmesh_billing_usage_units_total 0\n"


def record_request(method: str, endpoint: str, status_code: int, duration_s: float) -> None:
    pass


def record_webhook(source: str, event_type: str, status: str) -> None:
    pass


def record_workflow(workflow_type: str, duration_s: float) -> None:
    pass


def set_queue_depth(queue_name: str, depth: float, priority: str) -> None:
    pass


def record_retry(job_type: str, reason: str) -> None:
    pass


def record_provider_call(
    provider: str, model: str, duration_s: float, is_error: bool = False, error_type: str = ""
) -> None:
    pass


def record_tokens(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    pass


def record_finding(severity: str, rule_category: str, tenant_id: str) -> None:
    pass


def record_sandbox_failure(failure_reason: str, exit_code: int) -> None:
    pass


def record_billing_metric(metric_type: str, units: int | float, tenant_id: str) -> None:
    pass
