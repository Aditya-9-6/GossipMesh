import pytest
import time
from unittest.mock import patch

from gossipmesh.services.key_pool_router import (
    KeyMetrics,
    KeyPoolRouter,
    track_error_rate,
    mask_key,
)


def test_mask_key():
    assert mask_key("") == "<empty>"
    assert mask_key("short") == "***"
    assert mask_key("1234567890abcdef") == "1234...cdef"


def test_key_metrics_rolling_window():
    metrics = KeyMetrics()
    assert metrics.request_count() == 0
    assert metrics.error_rate() == 0.0

    # Add 4 requests: 1 error, 3 successes
    metrics.add(is_error=False)
    metrics.add(is_error=False)
    metrics.add(is_error=False)
    metrics.add(is_error=True)

    assert metrics.request_count() == 4
    assert metrics.error_rate() == 0.25


def test_router_key_rotation_and_cooldown():
    router = KeyPoolRouter(initial_keys=["key-alpha", "key-beta", "key-gamma"])
    assert len(router) == 3

    k1 = router.next_key()
    assert k1 == "key-alpha"

    # Simulate HTTP 429 on key-alpha -> immediate cooldown
    router.record("key-alpha", is_error=True, immediate=True)
    assert router.is_on_cooldown("key-alpha") is True

    # Next key should skip key-alpha and return key-beta
    k2 = router.next_key()
    assert k2 == "key-beta"

    # Next key should return key-gamma
    k3 = router.next_key()
    assert k3 == "key-gamma"


def test_router_threshold_cooldown():
    router = KeyPoolRouter(initial_keys=["key-threshold"])
    # 4 requests with 2 errors = 50% error rate > 0.25 threshold
    router.record("key-threshold", is_error=True, immediate=False)
    router.record("key-threshold", is_error=False, immediate=False)
    router.record("key-threshold", is_error=True, immediate=False)
    router.record("key-threshold", is_error=False, immediate=False)

    assert router.is_on_cooldown("key-threshold") is True


def test_track_error_rate_rotates_on_429():
    test_router = KeyPoolRouter(initial_keys=["key-failing", "key-healthy"])
    attempts_made = []

    @track_error_rate(router_instance=test_router)
    def call_gemini(prompt: str, api_key: str = ""):
        attempts_made.append(api_key)
        if api_key == "key-failing":
            raise RuntimeError("HTTP 429: ResourceExhausted rate limit")
        return f"Response for {prompt} with {api_key}"

    result = call_gemini("Generate architecture")
    assert result == "Response for Generate architecture with key-healthy"
    assert attempts_made == ["key-failing", "key-healthy"]
    # Failing key should now be in cooldown
    assert test_router.is_on_cooldown("key-failing") is True


def test_track_error_rate_exhaustion():
    test_router = KeyPoolRouter(initial_keys=["broken-key-1", "broken-key-2"])

    @track_error_rate(router_instance=test_router)
    def call_failing_api():
        raise RuntimeError("HTTP 503: Service Unavailable")

    with pytest.raises(RuntimeError) as exc_info:
        call_failing_api()

    assert "503" in str(exc_info.value)
