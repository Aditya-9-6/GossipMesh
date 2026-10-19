import time
import asyncio
from typing import Dict, Tuple


class TokenBucketRateLimiter:
    def __init__(self, capacity: float, refill_rate: float, max_tracked_peers: int = 10000):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.max_tracked_peers = max_tracked_peers
        self.buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    async def _evict_lru_if_needed(self) -> None:
        if len(self.buckets) >= self.max_tracked_peers:
            oldest_peer = min(self.buckets.keys(), key=lambda p: self.buckets[p][1])
            del self.buckets[oldest_peer]

    async def consume(self, peer_id: str, tokens: float = 1.0) -> bool:
        async with self._lock:
            now = time.monotonic()
            if peer_id not in self.buckets:
                await self._evict_lru_if_needed()
                self.buckets[peer_id] = (self.capacity, now)

            tokens_available, last_update = self.buckets[peer_id]
            delta = now - last_update
            tokens_available = min(self.capacity, tokens_available + delta * self.refill_rate)

            if tokens_available >= tokens:
                tokens_available -= tokens
                self.buckets[peer_id] = (tokens_available, now)
                return True
            else:
                self.buckets[peer_id] = (tokens_available, now)
                return False
