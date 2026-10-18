import time
import threading
from typing import Dict

class TokenBucketRateLimiter:
    """Decentralized O(1) token-bucket rate limiter for P2P peers with TTL/LRU eviction."""

    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0, max_buckets: int = 10000, ttl_seconds: float = 3600.0):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate) # tokens per second
        self.max_buckets = max_buckets
        self.ttl_seconds = ttl_seconds
        self.buckets: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def _evict_stale_or_overflow(self, now: float) -> None:
        if len(self.buckets) >= self.max_buckets:
            stale_keys = [
                pid for pid, bucket in self.buckets.items()
                if now - bucket["last_refill"] > self.ttl_seconds
            ]
            for pid in stale_keys:
                del self.buckets[pid]
            if len(self.buckets) >= self.max_buckets:
                # Evict oldest by last_refill if still at capacity
                oldest = sorted(self.buckets.items(), key=lambda x: x[1]["last_refill"])
                for pid, _ in oldest[:len(self.buckets) - self.max_buckets + 1]:
                    del self.buckets[pid]

    def allow(self, peer_id: str, cost: float = 1.0) -> bool:
        """Check if peer has enough tokens to consume cost. Returns True if allowed."""
        now = time.time()
        with self._lock:
            self._evict_stale_or_overflow(now)
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
