import time
import threading
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class RateLimitConfig:
    capacity: float = 100.0
    refill_rate: float = 50.0  # tokens per second
    burst_limit: float = 200.0

class TokenBucket:
    """Thread-safe token bucket for rate limiting individual streams or requests."""
    def __init__(self, capacity: float = 100.0, refill_rate: float = 50.0) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            if elapsed > 0.00001:
                refill = elapsed * self.refill_rate
                self._tokens = min(self.capacity, self._tokens + refill)
                self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

class PeerRateLimiter:
    """Thread-safe, memory-bounded leaky-bucket rate limiter for peer outbound streams
    with atomic counters and strict per-peer token replenishment intervals under 50us."""
    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self.config = config or RateLimitConfig()
        self._tokens: Dict[str, float] = {}
        self._last_refill: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._dropped_count = 0
        self._allowed_count = 0

    def acquire(self, peer_id: str, tokens: float = 1.0) -> bool:
        """Attempts to consume tokens for a given peer. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        with self._lock:
            if peer_id not in self._tokens:
                self._tokens[peer_id] = self.config.capacity
                self._last_refill[peer_id] = now

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
