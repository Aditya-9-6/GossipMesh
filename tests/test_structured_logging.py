import json
import logging
from gossipmesh.core.logging import (
    StructuredJSONFormatter,
    bind_logging_context,
    log_structured_event,
    redact_sensitive_data,
)


def test_structured_json_formatter_fields():
    formatter = StructuredJSONFormatter()
    record = logging.LogRecord(
        name="gossipmesh.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Task execution finished successfully",
        args=(),
        exc_info=None,
    )
    setattr(record, "event", "task.completed")
    setattr(record, "duration_ms", 124.5)

    with bind_logging_context(
        request_id="req-abc-999",
        workflow_id=101,
        job_id=202,
        organization_id=5,
    ):
        raw_output = formatter.format(record)
        data = json.loads(raw_output)

    assert data["level"] == "INFO"
    assert data["message"] == "Task execution finished successfully"
    assert data["request_id"] == "req-abc-999"
    assert data["workflow_id"] == "101"
    assert data["job_id"] == "202"
    assert data["organization_id"] == "5"
    assert data["event"] == "task.completed"
    assert data["duration_ms"] == 124.5
    assert "timestamp" in data
    assert "service" in data


def test_secret_redaction():
    # OpenAI / Stripe secret key
    text_with_sk = "Calling API using sk-test-key-1234567890123456789012"
    redacted_sk = redact_sensitive_data(text_with_sk)
    assert "sk-test-key" not in redacted_sk
    assert "[REDACTED_SECRET]" in redacted_sk

    # GitHub PAT
    text_with_ghp = "Authentication token: ghp_1234567890abcdef1234567890abcdef1234"
    redacted_ghp = redact_sensitive_data(text_with_ghp)
    assert "ghp_" not in redacted_ghp
    assert "[REDACTED_SECRET]" in redacted_ghp

    # Stripe webhook secret
    text_with_whsec = "Webhook signature key: whsec_1234567890abcdef1234567890"
    redacted_whsec = redact_sensitive_data(text_with_whsec)
    assert "whsec_" not in redacted_whsec
    assert "[REDACTED_SECRET]" in redacted_whsec

    # Bearer token
    text_with_bearer = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    redacted_bearer = redact_sensitive_data(text_with_bearer)
    assert "eyJhbGci" not in redacted_bearer
    assert "[REDACTED_TOKEN]" in redacted_bearer

    # Raw source code
    text_with_code = (
        "Error occurred in source:\ndef malicious_payload(x, y):\n    import os\n    return os.system('calc')\n"
    )
    redacted_code = redact_sensitive_data(text_with_code)
    assert "malicious_payload" not in redacted_code
    assert "[REDACTED_SOURCE_CODE]" in redacted_code


def test_log_structured_event(caplog):
    logger = logging.getLogger("gossipmesh.event_test")
    logger.setLevel(logging.INFO)

    with caplog.at_level(logging.INFO):
        log_structured_event(
            logger=logger,
            level=logging.ERROR,
            event="ci_fixer.timeout",
            message="Sandbox command timed out after 30s",
            duration_ms=30005.2,
            error_category="TIMEOUT_ERROR",
        )

    assert len(caplog.records) == 1
    rec = caplog.records[0]
    assert rec.event == "ci_fixer.timeout"
    assert rec.duration_ms == 30005.2
    assert rec.error_category == "TIMEOUT_ERROR"
