"""
Unit tests for P2P Leaky-Bucket and Token-Bucket Rate Limiter.
"""

import pytest
import asyncio
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig, LeakyBucket
from gossipmesh.p2p.transport import P2PTransport


@pytest.mark.asyncio
async def test_leaky_bucket_basic():
    bucket = LeakyBucket(capacity=5.0, leak_rate=10.0)
    assert await bucket.add(2.0) is True
    assert await bucket.add(3.0) is True
    assert await bucket.add(1.0) is False  # Exceeds capacity


@pytest.mark.asyncio
async def test_peer_rate_limiter_allow_and_drop():
    config = RateLimitConfig(
        max_rate_per_sec=5.0,
        burst_capacity=5.0,
        max_bandwidth_bytes_per_sec=1024.0,
        burst_bandwidth_bytes=1024.0,
        max_tracked_peers=10,
    )
    limiter = PeerRateLimiter(config)
    peer_id = "peer_alpha"

    # Consume within burst capacity
    for _ in range(5):
        assert await limiter.check_and_consume(peer_id, payload_size=100) is True

    # Next should be dropped
    assert await limiter.check_and_consume(peer_id, payload_size=100) is False
    assert limiter.metrics.dropped_messages == 1


@pytest.mark.asyncio
async def test_p2p_transport_integration():
    transport = P2PTransport()
    peer_id = "peer_beta"
    payload = b"Hello GossipMesh!"

    # First message should pass
    success = await transport.send_message(peer_id, payload)
    assert success is True
