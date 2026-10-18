import time
import asyncio
from typing import Dict, Tuple, Optional
from collections import deque, OrderedDict

class PeerTrafficMeter:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()

    def consume(self, tokens: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.last_refill = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class TokenBucketRateLimiter:
    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0, max_tracked_peers: int = 1000):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.max_tracked_peers = max_tracked_peers
        self._meters: OrderedDict[str, PeerTrafficMeter] = OrderedDict()
        self._lock = asyncio.Lock()

    async def acquire(self, peer_id: str, tokens: float = 1.0) -> bool:
        async with self._lock:
            if peer_id in self._meters:
                self._meters.move_to_end(peer_id)
                meter = self._meters[peer_id]
            else:
                if len(self._meters) >= self.max_tracked_peers:
                    self._meters.popitem(last=False)
                meter = PeerTrafficMeter(self.capacity, self.refill_rate)
                self._meters[peer_id] = meter
            return meter.consume(tokens)

    async def get_tokens(self, peer_id: str) -> float:
        async with self._lock:
            if peer_id not in self._meters:
                return self.capacity
            meter = self._meters[peer_id]
            now = time.monotonic()
            elapsed = now - meter.last_refill
            return min(meter.capacity, meter.tokens + elapsed * meter.refill_rate)
