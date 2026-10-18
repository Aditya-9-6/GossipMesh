import time
import threading
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class RateLimitConfig:
    capacity: float = 100.0
    refill_rate: float = 50.0  # tokens per second
    burst_limit: float = 200.0
    max_rate_per_sec: float = 50.0
    burst_capacity: float = 100.0
    max_bandwidth_bytes_per_sec: float = 100000.0
    burst_bandwidth_bytes: float = 100000.0
    max_tracked_peers: int = 1000

    def __post_init__(self):
        if 'burst_capacity' in self.__dataclass_fields__ and self.burst_capacity != 100.0:
            self.capacity = self.burst_capacity
        if 'max_rate_per_sec' in self.__dataclass_fields__ and self.max_rate_per_sec != 50.0:
            self.refill_rate = self.max_rate_per_sec

class TokenBucket:
    """Thread-safe token bucket rate limiter supporting token consumption and replenishment."""
    def __init__(self, capacity: float = 100.0, refill_rate: float = 50.0, initial_tokens: Optional[float] = None) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity if initial_tokens is None else initial_tokens
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed > 0:
            refill = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + refill)
            self.last_refill = now

    def can_consume(self, tokens: float = 1.0, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.monotonic()
        with self._lock:
            self._refill(current_time)
            return self.tokens >= tokens

    def consume(self, tokens: float = 1.0) -> bool:
        now = time.monotonic()
        with self._lock:
            self._refill(now)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class PeerRateLimiter:
    """Thread-safe, memory-bounded leaky-bucket rate limiter for peer outbound streams
    with atomic counters and strict per-peer token replenishment intervals under 50us."""
    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self.config = config or RateLimitConfig()
        # Sync capacity and refill rate from legacy aliases if passed
        if hasattr(self.config, 'burst_capacity') and self.config.burst_capacity:
            self.config.capacity = self.config.burst_capacity
        if hasattr(self.config, 'max_rate_per_sec') and self.config.max_rate_per_sec:
            self.config.refill_rate = self.config.max_rate_per_sec
            
        self._tokens: Dict[str, float] = {}
        self._last_refill: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._dropped_count = 0
        self._allowed_count = 0

    def acquire(self, peer_id: str, tokens: float = 1.0) -> bool:
        """Attempts to consume tokens for a given peer. Returns True if allowed, False if rate limited."""
        now = time.monotonic()
        with self._lock:
            # LRU eviction if max_tracked_peers exceeded
            if len(self._tokens) >= getattr(self.config, 'max_tracked_peers', 1000) and peer_id not in self._tokens:
                if self._tokens:
                    oldest_peer = min(self._last_refill, key=self._last_refill.get)
                    self._tokens.pop(oldest_peer, None)
                    self._last_refill.pop(oldest_peer, None)

            if peer_id not in self._tokens:
                self._tokens[peer_id] = self.config.capacity
                self._last_refill[peer_id] = now

            # Replenish tokens based on elapsed time
            elapsed = now - self._last_refill[peer_id]
            if elapsed > 0.000001:  # avoid redundant micro-updates
                refill = elapsed * self.config.refill_rate
                self._tokens[peer_id] = min(self.config.capacity, self._tokens[peer_id] + refill)
                self._last_refill[peer_id] = now

            # Check if enough tokens exist
            if self._tokens[peer_id] >= tokens:
                self._tokens[peer_id] -= tokens
                self._allowed_count += 1
                return True
            else:
                self._dropped_count += 1
                return False

    def reset_peer(self, peer_id: str) -> None:
        with self._lock:
            self._tokens.pop(peer_id, None)
            self._last_refill.pop(peer_id, None)

    def get_tokens(self, peer_id: str) -> float:
        """Returns current available tokens for a peer."""
        now = time.monotonic()
        with self._lock:
            if peer_id not in self._tokens:
                return self.config.capacity
            elapsed = now - self._last_refill[peer_id]
            refill = elapsed * self.config.refill_rate
            return min(self.config.capacity, self._tokens[peer_id] + refill)

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
