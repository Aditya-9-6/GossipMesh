import pytest
import asyncio
from gossipmesh.p2p.ratelimit import TokenBucket, LeakyBucketStreamLimiter, LeakyBucketConfig


def test_token_bucket_basic():
    bucket = TokenBucket(capacity=10.0, refill_rate=5.0)
    assert bucket.can_consume(5.0) is True
    assert bucket.consume(5.0) is True
    assert bucket.tokens == pytest.approx(5.0, abs=0.1)
    assert bucket.consume(6.0) is False


@pytest.mark.asyncio
async def test_leaky_bucket_stream_limiter():
    config = LeakyBucketConfig(capacity=5.0, refill_rate=10.0, max_tracked_peers=2)
    limiter = LeakyBucketStreamLimiter(config)

    peer_a = "peer_alpha"
    peer_b = "peer_beta"

    # Consume tokens for peer_a
    assert await limiter.acquire(peer_a, 3.0) is True
    assert await limiter.acquire(peer_a, 3.0) is False

    # Test adaptive leak rate adjustment with simulated socket latency
    adjusted = await limiter.adjust_leak_rate(peer_a, 0.1)
    assert adjusted < config.leak_rate

    # Test tracking limit & LRU eviction
    assert await limiter.acquire(peer_b, 1.0) is True
    metrics = limiter.get_metrics()
    assert metrics["allowed_messages"] >= 2
    assert metrics["dropped_messages"] >= 1
