"""
Unit tests for the GossipMesh P2P Leaky-Bucket & Token-Bucket Rate Limiter.
"""

import pytest
import asyncio
import time
from gossipmesh.p2p.ratelimit import (
    TokenBucket,
    LeakyBucketStreamLimiter,
    LeakyBucketConfig,
    RateLimitMetrics,
)


def test_token_bucket_basic():
    bucket = TokenBucket(capacity=10.0, refill_rate=5.0, initial_tokens=10.0)
    assert bucket.can_consume(5.0) is True
    assert bucket.consume(5.0) is True
    assert bucket.tokens == pytest.approx(5.0, abs=0.1)

    # Consume more than available
    assert bucket.consume(6.0) is False
    assert bucket.tokens == pytest.approx(5.0, abs=0.1)


def test_token_bucket_refill():
    bucket = TokenBucket(capacity=10.0, refill_rate=10.0, initial_tokens=0.0)
    now = time.monotonic()
    # Refill for 0.5 seconds -> should get 5 tokens
    assert bucket.can_consume(2.0, now=now + 0.5) is True
    assert bucket.consume(4.0, now=now + 0.5) is True
    assert bucket.tokens == pytest.approx(1.0, abs=0.1)


@pytest.mark.asyncio
async def test_leaky_bucket_stream_limiter_happy_path():
    config = LeakyBucketConfig(capacity=10.0, leak_rate=5.0, max_tracked_peers=10)
    limiter = LeakyBucketStreamLimiter(config)

    peer_id = "peer-node-1"
    # Consume initial burst
    for _ in range(10):
        assert await limiter.acquire(peer_id, tokens=1.0, payload_bytes=100) is True

    # Next consumption should fail immediately due to exhausted capacity
    assert await limiter.acquire(peer_id, tokens=1.0, payload_bytes=100) is False

    stats = await limiter.get_stats()
    assert stats["allowed_messages"] == 10
    assert stats["dropped_messages"] == 1
    assert stats["allowed_bytes"] == 1000
    assert stats["dropped_bytes"] == 100
    assert stats["tracked_peers"] == 1


@pytest.mark.asyncio
async def test_leaky_bucket_lru_eviction():
    config = LeakyBucketConfig(capacity=5.0, leak_rate=1.0, max_tracked_peers=2)
    limiter = LeakyBucketStreamLimiter(config)

    await limiter.acquire("peer-A", tokens=1.0)
    await limiter.acquire("peer-B", tokens=1.0)
    assert len(limiter._buckets) == 2

    # Access peer-A to make it recently used
    await limiter.acquire("peer-A", tokens=1.0)

    # Adding peer-C should evict peer-B (LRU)
    await limiter.acquire("peer-C", tokens=1.0)
    assert len(limiter._buckets) == 2
    assert "peer-B" not in limiter._buckets
    assert "peer-A" in limiter._buckets
    assert "peer-C" in limiter._buckets


@pytest.mark.asyncio
async def test_leaky_bucket_concurrent_access():
    config = LeakyBucketConfig(capacity=100.0, leak_rate=50.0, max_tracked_peers=100)
    limiter = LeakyBucketStreamLimiter(config)

    async def task(peer: str):
        return await limiter.acquire(peer, tokens=1.0, payload_bytes=50)

    results = await asyncio.gather(*(task(f"peer-{i % 5}") for i in range(200)))
    assert sum(1 for r in results if r) > 0
    stats = await limiter.get_stats()
    assert stats["allowed_messages"] + stats["dropped_messages"] == 200
