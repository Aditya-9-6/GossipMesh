"""
Unit Tests for Enterprise SaaS Telemetry Module
"""

import pytest
from enterprise.telemetry import (
    is_telemetry_enabled,
    sign_payload,
    report_telemetry_event,
)


def test_telemetry_disabled_by_default(monkeypatch):
    """Ensure telemetry is disabled when no endpoint is set or AIR_GAPPED=1."""
    monkeypatch.delenv("SAAS_ENDPOINT", raising=False)
    monkeypatch.setenv("AIR_GAPPED", "1")
    assert not is_telemetry_enabled()

    # Reporting event returns False without doing any network call
    result = report_telemetry_event(
        customer_id="defense-corp",
        event_type="test",
        bundle_id="b04",
        task_type="architecture",
    )
    assert result is False


def test_telemetry_enabled_flag(monkeypatch):
    """Ensure telemetry reports enabled when endpoint is explicitly supplied."""
    monkeypatch.delenv("AIR_GAPPED", raising=False)
    monkeypatch.setenv("SAAS_ENDPOINT", "https://api.yourdomain.com/v1/telemetry")
    assert is_telemetry_enabled()


def test_hmac_signature_calculation():
    """Verify HMAC-SHA256 signature calculation matches deterministic standard."""
    secret = "hmac_secret_key_placeholder"
    payload = b'{"customer_id":"acme"}'
    signature = sign_payload(payload, secret)

    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex string is 64 characters


def test_offline_resilience_on_network_failure(monkeypatch):
    """Air-gapped guarantee: Unreachable network endpoints MUST NOT crash the reviewer."""
    monkeypatch.delenv("AIR_GAPPED", raising=False)
    monkeypatch.setenv("SAAS_ENDPOINT", "https://127.0.0.1:59999/unreachable")
    monkeypatch.setenv("SAAS_TELEMETRY_SECRET", "test-secret")

    # This should fail cleanly and return False without throwing an unhandled exception
    result = report_telemetry_event(
        customer_id="test-customer",
        event_type="review_completed",
        bundle_id="b04",
        task_type="architecture",
        timeout_seconds=0.5,
    )
    assert result is False
