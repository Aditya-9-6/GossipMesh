import time
import threading
from dataclasses import dataclass
from typing import Dict, Any, Optional, OrderedDict

@dataclass
class RateLimitConfig:
    capacity: float = 100.0
    refill_rate: float = 50.0  # tokens per second
    burst_limit: float = 200.0
    max_rate_per_sec: Optional[float] = None
    burst_capacity: Optional[float] = None
    max_bandwidth_bytes_per_sec: Optional[float] = None
    burst_bandwidth_bytes: Optional[float] = None
    max_tracked_peers: int = 10000

    def __post_init__(self):
        if self.max_rate_per_sec is not None:
            self.refill_rate = self.max_rate_per_sec
        if self.burst_capacity is not None:
            self.capacity = self.burst_capacity
            self.burst_limit = self.burst_capacity

class TokenBucket:
    """Thread-safe Token Bucket rate limiter supporting basic consumption and refill."""
    def __init__(self, capacity: float, refill_rate: float, initial_tokens: Optional[float] = None) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = initial_tokens if initial_tokens is not None else capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed > 0:
            new_tokens = elapsed * self.refill_rate
            self._tokens = min(self.capacity, self._tokens + new_tokens)
            self._last_refill = now

    def consume(self, tokens: float = 1.0) -> bool:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

class PeerRateLimiter:
    """Thread-safe, memory-bounded leaky-bucket rate limiter for peer outbound streams
    with atomic counters and LRU eviction to prevent memory exhaustion."""
    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self.config = config or RateLimitConfig()
        self._tokens: OrderedDict[str, float] = OrderedDict()
        self._last_refill: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._dropped_count = 0
        self._allowed_count = 0
        self.max_tracked_peers = self.config.max_tracked_peers

    def acquire(self, peer_id: str, tokens: float = 1.0) -> bool:
        """Attempts to consume tokens for a given peer. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        with self._lock:
            if peer_id not in self._tokens:
                if len(self._tokens) >= self.max_tracked_peers:
                    # Evict oldest tracked peer (LRU)
                    oldest_peer, _ = self._tokens.popitem(last=False)
                    self._last_refill.pop(oldest_peer, None)
                self._tokens[peer_id] = self.config.capacity
                self._last_refill[peer_id] = now
            else:
                self._tokens.move_to_end(peer_id)

            # Replenish tokens based on elapsed time
            elapsed = now - self._last_refill[peer_id]
            if elapsed > 0.00001:  # avoid redundant micro-updates
                refill = elapsed * self.config.refill_rate
                self._tokens[peer_id] = min(self.config.burst_limit, self._tokens[peer_id] + refill)
                self._last_refill[peer_id] = now

            # Check if enough tokens exist
            if self._tokens[peer_id] >= tokens:
                self._tokens[peer_id] -= tokens
                self._allowed_count += 1
                return True
            else:
                self._dropped_count += 1
                return False

    def get_tokens(self, peer_id: str) -> float:
        """Returns current available tokens for a peer."""
        now = time.monotonic()
        with self._lock:
            if peer_id not in self._tokens:
                return self.config.capacity
            elapsed = now - self._last_refill[peer_id]
            refill = elapsed * self.config.refill_rate
            return min(self.config.burst_limit, self._tokens[peer_id] + refill)

    def reset_peer(self, peer_id: str) -> None:
        with self._lock:
            self._tokens.pop(peer_id, None)
            self._last_refill.pop(peer_id, None)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns rate limiter telemetry metrics."""
        with self._lock:
            return {
                "active_peers": len(self._tokens),
                "allowed_count": self._allowed_count,
                "dropped_count": self._dropped_count,
                "capacity": self.config.capacity,
                "refill_rate": self.config.refill_rate,
            }
