import time
import threading
from typing import Dict

class TokenBucketRateLimiter:
    """Decentralized O(1) token-bucket rate limiter for P2P peers."""

    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate) # tokens per second
        self.buckets: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def allow(self, peer_id: str, cost: float = 1.0) -> bool:
        """Check if peer has enough tokens to consume cost. Returns True if allowed."""
        now = time.time()
        with self._lock:
            bucket = self.buckets.get(peer_id)
            if not bucket:
                self.buckets[peer_id] = {"tokens": self.capacity - cost, "last_refill": now}
                return self.capacity >= cost

            elapsed = now - bucket["last_refill"]
            bucket["last_refill"] = now
            bucket["tokens"] = min(self.capacity, bucket["tokens"] + elapsed * self.refill_rate)

            if bucket["tokens"] >= cost:
                bucket["tokens"] -= cost
                return True
            return False

    def reset(self, peer_id: str) -> None:
        """Reset bucket for a peer."""
        with self._lock:
            if peer_id in self.buckets:
                del self.buckets[peer_id]
