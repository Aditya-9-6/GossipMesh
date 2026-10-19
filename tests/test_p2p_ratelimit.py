"""
Unit test suite for GossipMesh P2P Token-Bucket Rate Limiter & Transport Layer.
"""

import asyncio
import pytest
import time
from gossipmesh.p2p.ratelimit import (
    TokenBucket,
    RateLimitConfig,
    PeerRateLimiter,
)
from gossipmesh.p2p.transport import GossipTransport


class TestTokenBucket:
    def test_basic_consumption_and_refill(self):
        bucket = TokenBucket(capacity=5.0, refill_rate=2.0)
        assert bucket.consume(3.0) is True
        assert bucket.tokens == pytest.approx(2.0, rel=1e-2)
        assert bucket.consume(3.0) is False

        # Simulate time elapse
        future = time.monotonic() + 1.0
        assert bucket.can_consume(3.0, now=future) is True
        assert bucket.consume(3.0, now=future) is True

    def test_capacity_cap(self):
        bucket = TokenBucket(capacity=4.0, refill_rate=10.0, initial_tokens=2.0)
        future = time.monotonic() + 10.0
        bucket._refill(future)
        assert bucket.tokens == 4.0


@pytest.mark.asyncio
class TestPeerRateLimiter:
    async def test_frequency_limiting(self):
        config = RateLimitConfig(
            max_rate_per_sec=5.0,
            burst_capacity=3.0,
            max_bandwidth_bytes_per_sec=100000.0,
            burst_bandwidth_bytes=100000.0,
        )
        limiter = PeerRateLimiter(config=config)

        # 3 messages within burst should succeed
        for _ in range(3):
            allowed, reason = await limiter.check_and_consume("peer_a", 100)
            assert allowed is True
            assert reason == "ALLOWED"

        # 4th message exceeds frequency burst
        allowed, reason = await limiter.check_and_consume("peer_a", 100)
        assert allowed is False
        assert reason == "RATE_LIMIT_EXCEEDED"

    async def test_bandwidth_limiting(self):
        config = RateLimitConfig(
            max_rate_per_sec=100.0,
            burst_capacity=100.0,
            max_bandwidth_bytes_per_sec=1000.0,
            burst_bandwidth_bytes=2000.0,
        )
        limiter = PeerRateLimiter(config=config)

        # 1500 bytes allowed
        allowed, reason = await limiter.check_and_consume("peer_b", 1500)
        assert allowed is True

        # Next 1000 bytes exceeds remaining 500 bytes
        allowed, reason = await limiter.check_and_consume("peer_b", 1000)
        assert allowed is False
        assert reason == "BANDWIDTH_LIMIT_EXCEEDED"

    async def test_independent_peers(self):
        config = RateLimitConfig(burst_capacity=2.0, max_rate_per_sec=1.0)
        limiter = PeerRateLimiter(config=config)

        assert (await limiter.check_and_consume("peer1", 50))[0] is True
        assert (await limiter.check_and_consume("peer1", 50))[0] is True
        assert (await limiter.check_and_consume("peer1", 50))[0] is False

        # peer2 has its own fresh bucket
        assert (await limiter.check_and_consume("peer2", 50))[0] is True

    async def test_lru_eviction(self):
        config = RateLimitConfig(
            burst_capacity=10.0, max_rate_per_sec=1.0, max_tracked_peers=2
        )
        limiter = PeerRateLimiter(config=config)

        await limiter.check_and_consume("p1", 10)
        await limiter.check_and_consume("p2", 10)
        assert len(limiter.peers) == 2
        assert "p1" in limiter.peers

        # Adding 3rd peer evicts oldest (p1)
        await limiter.check_and_consume("p3", 10)
        assert len(limiter.peers) == 2
        assert "p1" not in limiter.peers
        assert "p2" in limiter.peers
        assert "p3" in limiter.peers

    async def test_telemetry_metrics(self):
        limiter = PeerRateLimiter(
            config=RateLimitConfig(burst_capacity=1.0, max_rate_per_sec=1.0)
        )
        await limiter.check_and_consume("peer_x", 128)
        await limiter.check_and_consume("peer_x", 256)  # dropped

        metrics = await limiter.get_metrics()
        assert metrics["allowed_messages"] == 1
        assert metrics["dropped_messages"] == 1
        assert metrics["allowed_bytes"] == 128
        assert metrics["dropped_bytes"] == 256
        assert metrics["tracked_peers_count"] == 1

    async def test_reset_peer(self):
        limiter = PeerRateLimiter(
            config=RateLimitConfig(burst_capacity=1.0, max_rate_per_sec=0.1)
        )
        await limiter.check_and_consume("peer_z", 10)
        assert (await limiter.check_and_consume("peer_z", 10))[0] is False

        await limiter.reset_peer("peer_z")
        # After reset, peer gets a fresh bucket
        assert (await limiter.check_and_consume("peer_z", 10))[0] is True


@pytest.mark.asyncio
class TestGossipTransport:
    async def test_receive_and_dispatch(self):
        transport = GossipTransport(node_id="node_test_1")
        received = []

        transport.register_handler("chat", lambda msg: received.append(msg))
        payload = {"text": "hello decentralized world"}
        result = await transport.receive_payload("peer_alpha", payload, topic="chat")

        assert result == payload
        assert len(received) == 1
        assert received[0]["text"] == "hello decentralized world"

    async def test_silent_drop_on_flood(self):
        config = RateLimitConfig(burst_capacity=2.0, max_rate_per_sec=0.1)
        transport = GossipTransport(node_id="node_test_2", config=config)

        res1 = await transport.receive_payload("spammer", {"msg": 1})
        res2 = await transport.receive_payload("spammer", {"msg": 2})
        res3 = await transport.receive_payload(
            "spammer", {"msg": 3}
        )  # dropped silently

        assert res1 is not None
        assert res2 is not None
        assert res3 is None

        telemetry = await transport.get_telemetry_metrics()
        assert telemetry["transport"]["received_messages"] == 2
        assert telemetry["transport"]["dropped_messages"] == 1

    async def test_payload_formats(self):
        transport = GossipTransport(node_id="node_test_formats")

        # bytes payload
        res_bytes = await transport.receive_payload("peer_b", b'{"key": "val"}')
        assert res_bytes == {"key": "val"}

        # raw string payload (non-json)
        res_str = await transport.receive_payload("peer_s", "plain text payload")
        assert res_str == {"raw": "plain text payload"}

        # int payload
        res_int = await transport.receive_payload("peer_i", 42)
        assert res_int == {"data": 42}

    async def test_handler_exception_handling(self):
        transport = GossipTransport(node_id="node_test_err")

        def buggy_handler(msg):
            raise RuntimeError("Bug in subscriber callback")

        transport.register_handler("test_err", buggy_handler)
        # Should not crash transport receive loop
        res = await transport.receive_payload(
            "peer_err", {"ok": True}, topic="test_err"
        )
        assert res == {"ok": True}

    async def test_send_payload(self):
        transport = GossipTransport(node_id="node_test_3")
        success = await transport.send_payload("peer_dest", {"data": "test_block"})
        assert success is True

        metrics = await transport.get_telemetry_metrics()
        assert metrics["transport"]["sent_messages"] == 1
        assert metrics["transport"]["sent_bytes"] > 0

    async def test_concurrent_consumption(self):
        config = RateLimitConfig(burst_capacity=50.0, max_rate_per_sec=10.0)
        limiter = PeerRateLimiter(config=config)

        async def worker(pid: str):
            for _ in range(5):
                await limiter.check_and_consume(pid, 20)
                await asyncio.sleep(0.001)

        tasks = [worker(f"worker_{i % 5}") for i in range(25)]
        await asyncio.gather(*tasks)

        metrics = await limiter.get_metrics()
        assert metrics["allowed_messages"] + metrics["dropped_messages"] == 125
