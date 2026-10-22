"""Unit tests for Secure Tenant-Scoped Redis Cache (Task 80)."""

import time
import pytest
from gossipmesh.semantic_cache import SecureRedisCache, SemanticCache


def test_tenant_isolation_in_cache():
    """Verify Tenant A cannot access Tenant B's cached responses."""
    cache = SecureRedisCache()
    prompt = "Review this pull request diff for SQL injection"

    cache.put(prompt, {"verdict": "APPROVED"}, organization_id="tenant_a", model="gemini")

    # Tenant A retrieves successfully
    assert cache.get(prompt, organization_id="tenant_a", model="gemini") == {"verdict": "APPROVED"}

    # Tenant B gets cache miss
    assert cache.get(prompt, organization_id="tenant_b", model="gemini") is None


def test_prompt_versioning_and_model_scoping():
    """Verify changing model or prompt version invalidates/misses cache."""
    cache = SecureRedisCache()
    prompt = "Analyze AST nodes"

    cache.put(prompt, {"ast": "ok"}, organization_id="tenant_1", model="gemini", prompt_version="v1")

    # Same model and version: hit
    assert cache.get(prompt, organization_id="tenant_1", model="gemini", prompt_version="v1") is not None

    # Different model: miss
    assert cache.get(prompt, organization_id="tenant_1", model="claude", prompt_version="v1") is None

    # Different prompt version: miss
    assert cache.get(prompt, organization_id="tenant_1", model="gemini", prompt_version="v2") is None


def test_pii_and_credential_redaction():
    """Verify API keys, tokens, and emails are redacted before writing to cache."""
    cache = SecureRedisCache()
    payload = {
        "finding": "Vulnerability found",
        "sample": "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'",
        "contact": "security-lead@company.com",
    }

    cache.put("leak_test", payload, organization_id="tenant_1")
    cached = cache.get("leak_test", organization_id="tenant_1")

    assert "[REDACTED_AWS_KEY]" in cached["sample"]
    assert "AKIAIOSFODNN7EXAMPLE" not in cached["sample"]
    assert "[REDACTED_EMAIL]" in cached["contact"]
    assert "security-lead@company.com" not in cached["contact"]


def test_cache_poisoning_detection_and_eviction():
    """Verify that tampering with stored payload triggers HMAC mismatch and eviction."""
    cache = SecureRedisCache()
    key = cache.build_key("tenant_1", "gemini", "default", "sensitive_prompt")

    cache.put("sensitive_prompt", {"result": "clean"}, organization_id="tenant_1")

    # Simulate attacker tampering with data in raw store
    tampered_raw = cache.client.get(key)
    tampered_envelope = eval(tampered_raw) if isinstance(tampered_raw, str) else tampered_raw
    import json

    envelope_dict = json.loads(tampered_raw)
    envelope_dict["data"] = {"result": "MALICIOUS_INJECTION_PAYLOAD"}
    cache.client.set(key, json.dumps(envelope_dict))

    # Attempt to read tampered key
    tampered_result = cache.get("sensitive_prompt", organization_id="tenant_1")

    # Invariant: Must reject tampered payload, record poisoning attempt, and purge poisoned entry
    assert tampered_result is None
    assert cache.poisoning_attempts == 1
    assert cache.client.get(key) is None  # Evicted!


def test_entry_size_limit_enforcement():
    """Verify entries exceeding max size limit (512 KB) are refused."""
    cache = SecureRedisCache()
    huge_payload = {"large_text": "X" * (600 * 1024)}  # 600 KB

    success = cache.put("huge_key", huge_payload, organization_id="tenant_1")
    assert success is False
    assert cache.rejected_size == 1
    assert cache.get("huge_key", organization_id="tenant_1") is None


def test_tenant_invalidation():
    """Verify invalidating a tenant clears only their keys."""
    cache = SecureRedisCache()

    cache.put("p1", {"data": 1}, organization_id="org_alpha")
    cache.put("p2", {"data": 2}, organization_id="org_alpha")
    cache.put("p3", {"data": 3}, organization_id="org_beta")

    deleted_count = cache.invalidate_tenant("org_alpha")
    assert deleted_count == 2

    assert cache.get("p1", organization_id="org_alpha") is None
    assert cache.get("p2", organization_id="org_alpha") is None
    assert cache.get("p3", organization_id="org_beta") is not None


def test_metrics_tracking():
    """Verify cache hits, misses, and hit rate metrics."""
    cache = SecureRedisCache()

    cache.put("item1", {"val": 10}, organization_id="t1")

    # 1 hit
    cache.get("item1", organization_id="t1")
    # 2 misses
    cache.get("nonexistent_1", organization_id="t1")
    cache.get("nonexistent_2", organization_id="t1")

    metrics = cache.get_metrics()
    assert metrics["hits"] == 1
    assert metrics["misses"] == 2
    assert metrics["hit_rate"] == round(1 / 3, 4)


def test_semantic_cache_backward_compatibility():
    """Verify SemanticCache wrapper works seamlessly for existing callers."""
    sem = SemanticCache()
    sem.put("legacy_key", {"status": "ok"})
    res = sem.get("legacy_key")
    assert res == {"status": "ok"}
