import pytest

try:
    from opentelemetry.trace import StatusCode
    from gossipmesh.observability.tracing import (
        get_memory_exporter,
        setup_tracer_provider,
        trace_api,
        trace_database,
        trace_github,
        trace_provider,
        trace_queue,
        trace_sandbox,
        trace_span,
        trace_webhook,
        trace_workflow,
    )

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False

pytestmark = pytest.mark.skipif(not HAS_OTEL, reason="opentelemetry not installed")


@pytest.fixture(autouse=True)
def clean_exporter():
    if not HAS_OTEL:
        pytest.skip("OpenTelemetry SDK not installed", allow_module_level=True)
    exporter = get_memory_exporter()
    exporter.clear()
    yield exporter
    exporter.clear()


def test_tracing_across_all_eight_layers(clean_exporter):
    if not HAS_OTEL:
        return
    with trace_workflow(workflow_id=404, workflow_type="issue_to_pr") as wf_span:
        with trace_api(endpoint="/api/v1/projects", method="GET"):
            pass
        with trace_webhook(source="github", event_type="issues.opened"):
            pass
        with trace_queue(queue_name="code_analysis", task_id="task_123"):
            pass
        with trace_github(operation="create_pull_request", repo="org/repo"):
            pass
        with trace_provider(provider="gemini", model="gemini-1.5-pro"):
            pass
        with trace_database(operation="SELECT", table="repositories"):
            pass
        with trace_sandbox(command="pytest -q", timeout_s=30.0):
            pass

    spans = clean_exporter.get_finished_spans()
    assert len(spans) == 8

    span_names = {s.name for s in spans}
    assert "Workflow issue_to_pr" in span_names
    assert "API GET /api/v1/projects" in span_names
    assert "Webhook github:issues.opened" in span_names
    assert "Queue code_analysis" in span_names
    assert "GitHub create_pull_request" in span_names
    assert "LLM gemini:gemini-1.5-pro" in span_names
    assert "DB SELECT repositories" in span_names
    assert "Sandbox Execute" in span_names


def test_trace_attributes_redact_secrets_and_source_code(clean_exporter):
    if not HAS_OTEL:
        return
    leaky_attrs = {
        "api_key": "sk-proj-supersecretkey12345678901234567890",
        "github_token": "ghp_1234567890abcdef1234567890abcdef1234",
        "webhook_secret": "whsec_abcdef123456789012345678",
        "auth_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        "source_dump": "def malicious_function():\n    import os\n    return os.system('calc')\n",
        "safe_int": 42,
    }

    with trace_span("Sensitive Operation", attributes=leaky_attrs):
        pass

    spans = clean_exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = spans[0].attributes

    assert "supersecretkey" not in str(attrs["api_key"])
    assert "[REDACTED_SECRET]" in str(attrs["api_key"])

    assert "ghp_" not in str(attrs["github_token"])
    assert "[REDACTED_SECRET]" in str(attrs["github_token"])

    assert "whsec_" not in str(attrs["webhook_secret"])
    assert "[REDACTED_SECRET]" in str(attrs["webhook_secret"])

    assert "eyJhbGci" not in str(attrs["auth_header"])
    assert "[REDACTED_TOKEN]" in str(attrs["auth_header"])

    assert "malicious_function" not in str(attrs["source_dump"])
    assert "[REDACTED_SOURCE_CODE]" in str(attrs["source_dump"])

    assert attrs["safe_int"] == 42


def test_span_exception_recording(clean_exporter):
    if not HAS_OTEL:
        return
    with pytest.raises(RuntimeError):
        with trace_span("Failing Operation"):
            raise RuntimeError("Database connection timed out")

    spans = clean_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status.status_code == StatusCode.ERROR
    assert "Database connection timed out" in span.status.description
    assert len(span.events) > 0
    assert span.events[0].name == "exception"
