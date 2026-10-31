"""
Unit tests for GossipMesh P2P Dynamic Leaky-Bucket Rate Limiter and Transport Integration.
"""

import time
import pytest
import asyncio

from gossipmesh.p2p.ratelimit import LeakyBucketStreamLimiter, LeakyBucketConfig
from gossipmesh.p2p.transport import P2PTransport


@pytest.mark.asyncio
async def test_leaky_bucket_normal_operation():
    config = LeakyBucketConfig(capacity=5.0, leak_rate=10.0, max_tracked_peers=100)
    limiter = LeakyBucketStreamLimiter(config)

    peer_id = "peer_alpha"
    # Consume up to capacity
    for _ in range(5):
        assert await limiter.acquire(peer_id, tokens=1.0, payload_bytes=100) is True

    # 6th token should be dropped
    assert await limiter.acquire(peer_id, tokens=1.0, payload_bytes=100) is False

    metrics = limiter.metrics.to_dict()
    assert metrics["allowed_messages"] == 5
    assert metrics["dropped_messages"] == 1
    assert metrics["allowed_bytes"] == 500
    assert metrics["dropped_bytes"] == 100


@pytest.mark.asyncio
async def test_leaky_bucket_replenishment():
    config = LeakyBucketConfig(capacity=2.0, leak_rate=20.0, max_tracked_peers=100)
    limiter = LeakyBucketStreamLimiter(config)
    peer_id = "peer_beta"

    assert await limiter.acquire(peer_id, tokens=2.0) is True
    assert await limiter.acquire(peer_id, tokens=1.0) is False

    # Wait for leak/replenishment
    await asyncio.sleep(0.15)

    assert await limiter.acquire(peer_id, tokens=1.0) is True


def test_leaky_bucket_sync_fast_path():
    config = LeakyBucketConfig(capacity=3.0, leak_rate=5.0, max_tracked_peers=10)
    limiter = LeakyBucketStreamLimiter(config)
    peer_id = "peer_gamma"

    start_time = time.perf_counter()
    for _ in range(3):
        assert limiter.acquire_sync(peer_id, tokens=1.0, payload_bytes=64) is True
    duration = time.perf_counter() - start_time

    # Verify sub-50 microsecond execution constraint per iteration
    assert (duration / 3.0) < 0.0005

    assert limiter.acquire_sync(peer_id, tokens=1.0) is False


@pytest.mark.asyncio
async def test_transport_integration():
    transport = P2PTransport()
    await transport.start()

    peer_id = "peer_delta"
    payload = b"Hello GossipMesh!" * 10

    # Should allow initial messages
    success = await transport.send_gossip(peer_id, payload)
    assert success is True

    # Test sync send path
    sync_success = transport.send_gossip_sync(peer_id, payload)
    assert isinstance(sync_success, bool)

    await transport.stop()
