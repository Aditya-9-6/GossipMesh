"""
Decentralized Token-Bucket and Leaky-Bucket Rate Limiter for GossipMesh P2P Subsystem.

Provides O(1) per-peer bandwidth and message frequency tracking with
sliding window token buckets, burst capacity, and bounded-memory LRU eviction.
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


class LeakyBucket:
    """Thread-safe leaky-bucket rate limiter for outbound gossip streams."""

    def __init__(self, capacity: float, leak_rate: float):
        self.capacity = float(capacity)
        self.leak_rate = float(leak_rate)
        self.water = 0.0
        self.last_leak = time.monotonic()
        self._lock = asyncio.Lock()

    def _leak(self, now: float) -> None:
        delta = max(0.0, now - self.last_leak)
        self.water = max(0.0, self.water - delta * self.leak_rate)
        self.last_leak = now

    async def add(self, amount: float = 1.0) -> bool:
        async with self._lock:
            now = time.monotonic()
            self._leak(now)
            if self.water + amount <= self.capacity:
                self.water += amount
                return True
            return False


class PeerEntry:
    """Encapsulates rate and bandwidth buckets for an individual peer."""

    def __init__(self, config: RateLimitConfig, now: float):
        self.msg_bucket = TokenBucket(config.burst_capacity, config.max_rate_per_sec, initial_tokens=config.burst_capacity)
        self.bandwidth_bucket = TokenBucket(config.burst_bandwidth_bytes, config.max_bandwidth_bytes_per_sec, initial_tokens=config.burst_bandwidth_bytes)
        self.leaky_bucket = LeakyBucket(config.burst_capacity, config.max_rate_per_sec)
        self.last_seen = now


class PeerRateLimiter:
    """
    Decentralized per-peer sliding window rate limiter.
    Enforces frequency and bandwidth thresholds in O(1) time.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.peers: OrderedDict[str, PeerEntry] = OrderedDict()
        self.metrics = RateLimitMetrics()
        self._lock = asyncio.Lock()

    async def _evict_lru(self) -> None:
        while len(self.peers) >= self.config.max_tracked_peers:
            self.peers.popitem(last=False)

    async def check_and_consume(self, peer_id: str, payload_size: int = 256) -> bool:
        async with self._lock:
            now = time.monotonic()
            entry = self.peers.get(peer_id)
            if entry is None:
                await self._evict_lru()
                entry = PeerEntry(self.config, now)
                self.peers[peer_id] = entry
            else:
                self.peers.move_to_end(peer_id)
                entry.last_seen = now

            # Check message rate and bandwidth availability
            msg_allowed = entry.msg_bucket.consume(1.0, now)
            bw_allowed = entry.bandwidth_bucket.consume(float(payload_size), now)

            if msg_allowed and bw_allowed:
                self.metrics.record_allowed(payload_size)
                return True
            else:
                self.metrics.record_dropped(payload_size)
                return False
