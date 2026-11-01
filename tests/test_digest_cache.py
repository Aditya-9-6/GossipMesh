"""Unit tests for LruDigestCache."""

import time
import pytest
from gossipmesh.p2p.digest import LruDigestCache


def test_lru_digest_cache_basic():
    cache = LruDigestCache(capacity=3, default_ttl=10.0)
    cache.add("a", 1)
    cache.add("b", 2)
    cache.add("c", 3)

    assert cache.contains("a") is True
    assert cache.get("a") == 1
    assert cache.get_size() == 3

    # Adding fourth item should evict LRU ("b" since "a" was accessed)
    cache.add("d", 4)
    assert cache.contains("b") is False
    assert cache.contains("a") is True
    assert cache.contains("d") is True
    assert cache.get_size() == 3


def test_lru_digest_cache_ttl():
    cache = LruDigestCache(capacity=10, default_ttl=0.1)
    now = time.monotonic()
    cache.add("expire_soon", 42, ttl=0.05, now=now)
    cache.add("expire_later", 84, ttl=1.0, now=now)

    assert cache.contains("expire_soon", now=now + 0.02) is True
    assert cache.contains("expire_soon", now=now + 0.08) is False
    assert cache.contains("expire_later", now=now + 0.08) is True


if __name__ == "__main__":
    pytest.main([__file__])
