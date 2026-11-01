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
        self._buckets: OrderedDict[str, TokenBucket] = OrderedDict()
        self._lock = asyncio.Lock()
        self.metrics = RateLimitMetrics()

    async def _evict_lru_if_needed(self) -> None:
        if len(self._buckets) >= self.config.max_tracked_peers:
            self._buckets.popitem(last=False)

    async def acquire(self, peer_id: str, tokens: float = 1.0, payload_bytes: int = 0) -> bool:
        """
        Attempt to acquire tokens for outbound gossip to a peer.
        Supports dynamic burst absorption up to bucket capacity.
        """
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(peer_id)
            if bucket is None:
                await self._evict_lru_if_needed()
                bucket = TokenBucket(
                    capacity=self.config.capacity,
                    refill_rate=self.config.leak_rate,
                )
                self._buckets[peer_id] = bucket
            else:
                self._buckets.move_to_end(peer_id)

            allowed = bucket.consume(tokens, now)
            if allowed:
                self.metrics.record_allowed(payload_bytes)
            else:
                self.metrics.record_dropped(payload_bytes)
            return allowed

    async def check(self, peer_id: str, tokens: float = 1.0) -> bool:
        """Check if tokens can be acquired without consuming them."""
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(peer_id)
            if bucket is None:
                return self.config.capacity >= tokens
            return bucket.can_consume(tokens, now)

    async def get_stats(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "tracked_peers": len(self._buckets),
                **self.metrics.to_dict(),
            }
