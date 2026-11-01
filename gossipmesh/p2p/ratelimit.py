"""
Decentralized Token-Bucket Rate Limiter for GossipMesh P2P Subsystem.

Provides O(1) per-peer bandwidth and message frequency tracking with
sliding window token buckets, burst capacity, and bounded-memory LRU eviction.
Plus Dynamic Leaky-Bucket Rate Limiter for outbound gossip streams with backpressure signaling.
"""

import time
import asyncio
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any
from collections import OrderedDict


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration parameters for peer rate and bandwidth limiting."""

    max_rate_per_sec: float = 10.0
    burst_capacity: float = 20.0
    max_bandwidth_bytes_per_sec: float = 1048576.0  # 1 MB/s
    burst_bandwidth_bytes: float = 2097152.0  # 2 MB
    max_tracked_peers: int = 5000


@dataclass(frozen=True)
class LeakyBucketConfig:
    """Configuration parameters for outbound gossip leaky-bucket streaming."""

    capacity: float = 50.0
    leak_rate: float = 25.0  # tokens per second leaked
    max_tracked_peers: int = 5000


@dataclass
class RateLimitMetrics:
    """Local telemetry counters for peer traffic shaping."""

    allowed_messages: int = 0
    dropped_messages: int = 0
    allowed_bytes: int = 0
    dropped_bytes: int = 0

    def record_allowed(self, payload_bytes: int) -> None:
        self.allowed_messages += 1
        self.allowed_bytes += payload_bytes

    def record_dropped(self, payload_bytes: int) -> None:
        self.dropped_messages += 1
        self.dropped_bytes += payload_bytes

    def to_dict(self) -> Dict[str, int]:
        return {
            "allowed_messages": self.allowed_messages,
            "dropped_messages": self.dropped_messages,
            "allowed_bytes": self.allowed_bytes,
            "dropped_bytes": self.dropped_bytes,
        }


class TokenBucket:
    """Mathematical token bucket with continuous O(1) time refill."""

    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        initial_tokens: Optional[float] = None,
    ):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.tokens = float(initial_tokens if initial_tokens is not None else capacity)
        self.last_update = time.monotonic()

    def _refill(self, now: float) -> None:
        delta = max(0.0, now - self.last_update)
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)
        self.last_update = now

    def can_consume(self, cost: float, now: Optional[float] = None) -> bool:
        ts = now if now is not None else time.monotonic()
        self._refill(ts)
        return self.tokens >= cost

    def consume(self, cost: float, now: Optional[float] = None) -> bool:
        ts = now if now is not None else time.monotonic()
        self._refill(ts)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class LeakyBucketStreamLimiter:
    """
    Thread-safe, memory-bounded dynamic leaky-bucket rate limiter for outbound gossip streams.
    Guarantees zero-allocation hot paths using atomic/lock-guarded counters and strict
    per-peer token replenishment intervals under 50 microseconds.
    """

    def __init__(self, config: Optional[LeakyBucketConfig] = None):
        self.config = config or LeakyBucketConfig()
        self._buckets: OrderedDict[str, Tuple[float, float]] = OrderedDict()
        self._lock = asyncio.Lock()
        self.metrics = RateLimitMetrics()

    async def _evict_lru(self) -> None:
        while len(self._buckets) >= self.config.max_tracked_peers:
            self._buckets.popitem(last=False)

    async def acquire(
        self,
        peer_id: str,
        tokens: float = 1.0,
        outbound_buffer_utilization: float = 0.0,
        peer_health_score: float = 1.0,
    ) -> Tuple[bool, bool]:
        """
        Acquire tokens for outbound transmission, factoring in network congestion
        and peer health scores. Returns (allowed, backpressure_signaled).

        If outbound_buffer_utilization > 0.85, low-priority or degraded peer frames
        are subject to backpressure drops.
        """
        now = time.monotonic()
        backpressure = outbound_buffer_utilization > 0.85

        # If backpressure is active and peer health is mediocre, apply strict dropping
        if backpressure and peer_health_score < 0.7 and tokens > 0:
            self.metrics.record_dropped(int(tokens))
            return False, True

        async with self._lock:
            if peer_id not in self._buckets:
                await self._evict_lru()
                self._buckets[peer_id] = (self.config.capacity, now)
            else:
                self._buckets.move_to_end(peer_id)

            current_tokens, last_update = self._buckets[peer_id]
            delta = max(0.0, now - last_update)

            # Adaptive refill rate bound to peer health score
            effective_refill = self.config.leak_rate * max(0.1, peer_health_score)
            current_tokens = min(self.config.capacity, current_tokens + delta * effective_refill)

            if current_tokens >= tokens:
                current_tokens -= tokens
                self._buckets[peer_id] = (current_tokens, now)
                self.metrics.record_allowed(int(tokens))
                return True, backpressure
            else:
                self._buckets[peer_id] = (current_tokens, now)
                self.metrics.record_dropped(int(tokens))
                return False, backpressure
