import pytest
import asyncio
from gossipmesh.p2p.ratelimit import TokenBucket, LeakyBucketStreamLimiter, LeakyBucketConfig, RateLimitConfig


def test_token_bucket_basic():
    bucket = TokenBucket(capacity=10.0, refill_rate=5.0, initial_tokens=10.0)
    assert bucket.can_consume(5.0)
    assert bucket.consume(5.0) is True
    assert bucket.consume(10.0) is False


@pytest.mark.asyncio
async def test_leaky_bucket_stream_limiter_happy_path():
    limiter = LeakyBucketStreamLimiter(LeakyBucketConfig(capacity=10.0, leak_rate=5.0))
    allowed, bp = await limiter.acquire("peer_1", tokens=2.0, outbound_buffer_utilization=0.5, peer_health_score=1.0)
    assert allowed is True
    assert bp is False
    assert limiter.metrics.allowed_messages == 1


@pytest.mark.asyncio
async def test_leaky_bucket_backpressure_signaling():
    limiter = LeakyBucketStreamLimiter(LeakyBucketConfig(capacity=10.0, leak_rate=5.0))
    # Utilization > 0.85 triggers backpressure flag
    allowed, bp = await limiter.acquire(
        "peer_unhealthy", tokens=2.0, outbound_buffer_utilization=0.90, peer_health_score=0.4
    )
    assert allowed is False
    assert bp is True
    assert limiter.metrics.dropped_messages == 1


@pytest.mark.asyncio
async def test_leaky_bucket_lru_eviction():
    config = LeakyBucketConfig(capacity=10.0, leak_rate=5.0, max_tracked_peers=2)
    limiter = LeakyBucketStreamLimiter(config)

    await limiter.acquire("peer_a", tokens=1.0)
    await limiter.acquire("peer_b", tokens=1.0)
    assert len(limiter._buckets) == 2

    # Adding a 3rd peer should evict peer_a (LRU)
    await limiter.acquire("peer_c", tokens=1.0)
    assert len(limiter._buckets) == 2
    assert "peer_a" not in limiter._buckets
    assert "peer_b" in limiter._buckets
    assert "peer_c" in limiter._buckets
