import time
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class TokenBucketConfig:
    capacity: float = 1024.0 * 1024.0  # 1 MB bucket capacity
    refill_rate: float = 100.0 * 1024.0  # 100 KB/s refill rate


class LeakyBucketTrafficShaper:
    """Thread-safe leaky-bucket / token-bucket traffic shaper enforcing strict per-peer bandwidth caps."""

    def __init__(self, config: Optional[TokenBucketConfig] = None) -> None:
        self.config = config or TokenBucketConfig()
        self.tokens = self.config.capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
        self.total_shaped_bytes = 0
        self.total_dropped_bytes = 0

    def _refill_unlocked(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed > 0:
            added = elapsed * self.config.refill_rate
            self.tokens = min(self.config.capacity, self.tokens + added)
            self.last_refill = now

    def consume(self, cost_bytes: int, now: Optional[float] = None) -> bool:
        """Attempts to consume tokens for a packet of given size. Returns True if permitted."""
        if cost_bytes <= 0:
            return True
        current_time = now if now is not None else time.time()
        with self._lock:
            self._refill_unlocked(current_time)
            if self.tokens >= cost_bytes:
                self.tokens -= cost_bytes
                self.total_shaped_bytes += cost_bytes
                return True
            else:
                self.total_dropped_bytes += cost_bytes
                return False

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "capacity": self.config.capacity,
                "refill_rate": self.config.refill_rate,
                "current_tokens": self.tokens,
                "total_shaped_bytes": self.total_shaped_bytes,
                "total_dropped_bytes": self.total_dropped_bytes,
            }


class PeerTrafficShaperManager:
    """Manages independent leaky bucket traffic shapers per peer."""

    def __init__(self, default_config: Optional[TokenBucketConfig] = None) -> None:
        self.default_config = default_config or TokenBucketConfig()
        self._shapers: Dict[str, LeakyBucketTrafficShaper] = {}
        self._lock = threading.Lock()

    def get_shaper(self, peer_id: str) -> LeakyBucketTrafficShaper:
        with self._lock:
            if peer_id not in self._shapers:
                self._shapers[peer_id] = LeakyBucketTrafficShaper(self.default_config)
            return self._shapers[peer_id]

    def remove_peer(self, peer_id: str) -> None:
        with self._lock:
            self._shapers.pop(peer_id, None)
