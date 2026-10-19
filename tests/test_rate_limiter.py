import pytest
import asyncio
from gossipmesh.p2p.rate_limiter import TokenBucketRateLimiter
from gossipmesh.p2p.connection_manager import ConnectionManager

@pytest.mark.asyncio
async def test_rate_limiter_basic():
    limiter = TokenBucketRateLimiter(capacity=2.0, refill_rate=1.0)
    assert await limiter.consume("peer1", 1.0) is True
    assert await limiter.consume("peer1", 1.0) is True
    assert await limiter.consume("peer1", 1.0) is False
    await asyncio.sleep(1.1)
    assert await limiter.consume("peer1", 1.0) is True

@pytest.mark.asyncio
async def test_rate_limiter_memory_bound():
    limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=1.0, max_tracked_peers=2)
    assert await limiter.consume("peerA") is True
    assert await limiter.consume("peerB") is True
    assert "peerA" in limiter.buckets
    assert "peerB" in limiter.buckets
    assert await limiter.consume("peerC") is True
    assert "peerC" in limiter.buckets
    assert "peerA" not in limiter.buckets

@pytest.mark.asyncio
async def test_connection_manager_admission():
    manager = ConnectionManager(max_connections=2, capacity=10.0, refill_rate=1.0)
    assert await manager.admit_peer("p1", priority=1) is True
    assert await manager.admit_peer("p2", priority=2) is True
    assert len(manager.active_connections) == 2
    assert await manager.admit_peer("p3", priority=3) is True
    assert "p1" not in manager.active_connections
    assert "p3" in manager.active_connections
    assert await manager.admit_peer("p4", priority=0) is False
