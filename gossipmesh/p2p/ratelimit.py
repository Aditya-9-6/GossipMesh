import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any
from collections import OrderedDict

@dataclass
class RateLimitConfig:
    """Configuration parameters for peer rate and bandwidth limiting."""
    max_tokens: float = 100.0
    refill_rate: float = 20.0
    max_bytes_per_sec: float = 1048576.0  # 1 MB/s
    max_peers: int = 1000
    window_size_seconds: float = 60.0
    max_rate_per_sec: Optional[float] = None
    burst_capacity: Optional[float] = None
    max_bandwidth_bytes_per_sec: Optional[float] = None
    burst_bandwidth_bytes: Optional[float] = None

    def __post_init__(self):
        if self.max_rate_per_sec is not None:
            object.__setattr__(self, 'refill_rate', self.max_rate_per_sec)
        if self.burst_capacity is not None:
            object.__setattr__(self, 'max_tokens', self.burst_capacity)
        if self.max_bandwidth_bytes_per_sec is not None:
            object.__setattr__(self, 'max_bytes_per_sec', self.max_bandwidth_bytes_per_sec)
        elif self.burst_bandwidth_bytes is not None:
            object.__setattr__(self, 'max_bytes_per_sec', self.burst_bandwidth_bytes)

@dataclass
class RateLimitMetrics:
    """Local telemetry counters for peer traffic shaping."""
    allowed_count: int = 0
    dropped_count: int = 0
    allowed_bytes: int = 0
    dropped_bytes: int = 0

    def record_allowed(self, payload_bytes: int) -> None:
        self.allowed_count += 1
        self.allowed_bytes += payload_bytes

    def record_dropped(self, payload_bytes: int) -> None:
        self.dropped_count += 1
        self.dropped_bytes += payload_bytes

    def to_dict(self) -> Dict[str, int]:
        return {
            "allowed_messages": self.allowed_count,
            "dropped_messages": self.dropped_count,
            "allowed_bytes": self.allowed_bytes,
            "dropped_bytes": self.dropped_bytes,
            "allowed_count": self.allowed_count,
            "dropped_count": self.dropped_count,
        }

class TokenBucket:
    """Mathematical token bucket with continuous O(1) time refill."""
    def __init__(self, capacity: float, refill_rate: float, initial_tokens: Optional[float] = None):
        self.capacity = max(0.0, capacity)
        self.refill_rate = max(0.0, refill_rate)
        initial = capacity if initial_tokens is None else min(initial_tokens, capacity)
        self.tokens = max(0.0, initial)
        self.last_refill_timestamp = time.monotonic()

    def _refill(self, now: float) -> None:
        elapsed = now - self.last_refill_timestamp
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill_timestamp = now

    def can_consume(self, cost: float, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.monotonic()
        self._refill(current_time)
        return self.tokens >= cost

    def consume(self, cost: float, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.monotonic()
        self._refill(current_time)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

class PeerEntry:
    """Encapsulates rate and bandwidth buckets for an individual peer."""
    def __init__(self, config: RateLimitConfig, now: float):
        rate_cap = config.max_tokens if config.burst_capacity is None else config.burst_capacity
        rate_refill = config.refill_rate if config.max_rate_per_sec is None else config.max_rate_per_sec
        bw_cap = config.max_bytes_per_sec
        
        self.rate_bucket = TokenBucket(capacity=rate_cap, refill_rate=rate_refill, initial_tokens=rate_cap)
        self.bandwidth_bucket = TokenBucket(capacity=bw_cap, refill_rate=bw_cap, initial_tokens=bw_cap)
        self.last_seen = now

class PeerRateLimiter:
    """Decentralized per-peer sliding window rate limiter.
Enforces frequency and bandwidth thresholds in O(1) time."""
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._peers: OrderedDict[str, PeerEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self.metrics = RateLimitMetrics()

    def _evict_lru_if_full(self) -> None:
        while len(self._peers) >= self.config.max_peers:
            self._peers.popitem(last=False)

    def _get_or_create_peer(self, peer_id: str, now: float) -> PeerEntry:
        if peer_id in self._peers:
            self._peers.move_to_end(peer_id)
            entry = self._peers[peer_id]
            entry.last_seen = now
            return entry
        
        self._evict_lru_if_full()
        entry = PeerEntry(self.config, now)
        self._peers[peer_id] = entry
        return entry

    async def check_and_consume(self, peer_id: str, payload_size_bytes: int = 1) -> Tuple[bool, str]:
        """Validates whether incoming peer message complies with rate and bandwidth caps.
Returns (is_allowed, reason)."""
        now = time.monotonic()
        async with self._lock:
            peer = self._get_or_create_peer(peer_id, now)
            
            if not peer.rate_bucket.can_consume(1.0, now):
                self.metrics.record_dropped(payload_size_bytes)
                return False, "rate_limit_exceeded"
            
            if not peer.bandwidth_bucket.can_consume(float(payload_size_bytes), now):
                self.metrics.record_dropped(payload_size_bytes)
                return False, "bandwidth_limit_exceeded"
            
            peer.rate_bucket.consume(1.0, now)
            peer.bandwidth_bucket.consume(float(payload_size_bytes), now)
            self.metrics.record_allowed(payload_size_bytes)
            return True, "allowed"

    async def get_metrics(self) -> Dict[str, Any]:
        """Returns local telemetry metrics and active peer count."""
        async with self._lock:
            res = self.metrics.to_dict()
            count = len(self._peers)
            res["active_peers"] = count
            res["tracked_peers_count"] = count
            return res

    async def reset_peer(self, peer_id: str) -> None:
        """Removes a peer record from active tracking table."""
        async with self._lock:
            if peer_id in self._peers:
                del self._peers[peer_id]
