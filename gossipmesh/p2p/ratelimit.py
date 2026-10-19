import time
from typing import Dict, Tuple, Optional
import threading

class RateLimitConfig:
    def __init__(self, max_rate_per_sec: float = 10.0, burst_capacity: float = 10.0, max_bandwidth_bytes_per_sec: float = 1048576.0, burst_bandwidth_bytes: float = 1048576.0, max_tracked_peers: int = 1000) -> None:
        self.max_rate_per_sec = max_rate_per_sec
        self.burst_capacity = burst_capacity
        self.max_bandwidth_bytes_per_sec = max_bandwidth_bytes_per_sec
        self.burst_bandwidth_bytes = burst_bandwidth_bytes
        self.max_tracked_peers = max_tracked_peers

class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

    def can_consume(self, tokens: float, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.monotonic()
        with self._lock:
            self._refill(current_time)
            return self.tokens >= tokens

    def consume(self, tokens: float, now: Optional[float] = None) -> bool:
        current_time = now if now is not None else time.monotonic()
        with self._lock:
            self._refill(current_time)
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def acquire(self, tokens: float = 1.0) -> bool:
        return self.consume(tokens)

class PeerRateLimiter:
    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self.config = config or RateLimitConfig()
        self._msg_buckets: Dict[str, TokenBucket] = {}
        self._bytes_buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def _get_buckets(self, peer_id: str) -> Tuple[TokenBucket, TokenBucket]:
        if peer_id not in self._msg_buckets:
            if len(self._msg_buckets) >= self.config.max_tracked_peers:
                # Evict oldest or first
                oldest_key = next(iter(self._msg_buckets))
                self._msg_buckets.pop(oldest_key, None)
                self._bytes_buckets.pop(oldest_key, None)
            self._msg_buckets[peer_id] = TokenBucket(self.config.burst_capacity, self.config.max_rate_per_sec)
            self._bytes_buckets[peer_id] = TokenBucket(self.config.burst_bandwidth_bytes, self.config.max_bandwidth_bytes_per_sec)
        return self._msg_buckets[peer_id], self._bytes_buckets[peer_id]

    async def check_and_consume(self, peer_id: str, payload_size: int = 0) -> Tuple[bool, str]:
        with self._lock:
            msg_bucket, bytes_bucket = self._get_buckets(peer_id)
        
        now = time.monotonic()
        if not msg_bucket.can_consume(1.0, now=now):
            return False, "Rate limit exceeded (message count)"
        if payload_size > 0 and not bytes_bucket.can_consume(float(payload_size), now=now):
            return False, "Rate limit exceeded (bandwidth)"

        msg_bucket.consume(1.0, now=now)
        if payload_size > 0:
            bytes_bucket.consume(float(payload_size), now=now)
        return True, "OK"

    def acquire(self, peer_id: str) -> bool:
        with self._lock:
            msg_bucket, _ = self._get_buckets(peer_id)
        return msg_bucket.consume(1.0)

    def reset(self, peer_id: str) -> None:
        with self._lock:
            self._msg_buckets.pop(peer_id, None)
            self._bytes_buckets.pop(peer_id, None)
