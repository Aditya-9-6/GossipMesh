"""
Decentralized Token-Bucket Rate Limiter for GossipMesh P2P Subsystem.

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


class PeerEntry:
    """Encapsulates rate and bandwidth buckets for an individual peer."""

    def __init__(self, config: RateLimitConfig, now: float):
        self.msg_bucket = TokenBucket(config.burst_capacity, config.max_rate_per_sec)
        self.bandwidth_bucket = TokenBucket(
            config.burst_bandwidth_bytes, config.max_bandwidth_bytes_per_sec
        )
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

    def _evict_lru_if_full(self) -> None:
        while len(self.peers) >= self.config.max_tracked_peers:
            self.peers.popitem(last=False)

    def _get_or_create_peer(self, peer_id: str, now: float) -> PeerEntry:
        if peer_id in self.peers:
            self.peers.move_to_end(peer_id)
            return self.peers[peer_id]
        self._evict_lru_if_full()
        entry = PeerEntry(self.config, now)
        self.peers[peer_id] = entry
        return entry

    async def check_and_consume(
        self, peer_id: str, payload_size_bytes: int = 1
    ) -> Tuple[bool, str]:
        """
        Validates whether incoming peer message complies with rate and bandwidth caps.
        Returns (is_allowed, reason).
        """
        async with self._lock:
            now = time.monotonic()
            entry = self._get_or_create_peer(peer_id, now)
            entry.last_seen = now

            # Check frequency token
            if not entry.msg_bucket.can_consume(1.0, now):
                self.metrics.record_dropped(payload_size_bytes)
                return False, "RATE_LIMIT_EXCEEDED"

            # Check bandwidth token
            if not entry.bandwidth_bucket.can_consume(float(payload_size_bytes), now):
                self.metrics.record_dropped(payload_size_bytes)
                return False, "BANDWIDTH_LIMIT_EXCEEDED"

            # Consume both tokens atomically
            entry.msg_bucket.consume(1.0, now)
            entry.bandwidth_bucket.consume(float(payload_size_bytes), now)
            self.metrics.record_allowed(payload_size_bytes)
            return True, "ALLOWED"

    async def get_metrics(self) -> Dict[str, Any]:
        """Returns local telemetry metrics and active peer count."""
        async with self._lock:
            data = self.metrics.to_dict()
            data["tracked_peers_count"] = len(self.peers)
            return data

    async def reset_peer(self, peer_id: str) -> None:
        """Removes a peer record from active tracking table."""
        async with self._lock:
            if peer_id in self.peers:
                del self.peers[peer_id]
