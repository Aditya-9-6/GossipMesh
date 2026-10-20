import asyncio
import heapq
from typing import Dict, Set, Tuple, Any, List
from gossipmesh.p2p.rate_limiter import TokenBucketRateLimiter


class ConnectionManager:
    def __init__(self, max_connections: int = 100, capacity: float = 50.0, refill_rate: float = 10.0):
        self.max_connections = max_connections
        self.rate_limiter = TokenBucketRateLimiter(capacity=capacity, refill_rate=refill_rate)
        self.active_connections: Set[str] = set()
        self.connection_priorities: Dict[str, int] = {}
        self._pq: List[Tuple[int, float, str]] = []
        self._lock = asyncio.Lock()

    async def admit_peer(self, peer_id: str, priority: int = 0) -> bool:
        async with self._lock:
            if not await self.rate_limiter.consume(peer_id):
                return False
            if peer_id in self.active_connections:
                return True
            if len(self.active_connections) >= self.max_connections:
                if not self._pq:
                    return False
                lowest_priority, _, evicted_peer = heapq.heappop(self._pq)
                if priority <= lowest_priority:
                    heapq.heappush(self._pq, (lowest_priority, asyncio.get_event_loop().time(), evicted_peer))
                    return False
                self.active_connections.remove(evicted_peer)
                if evicted_peer in self.connection_priorities:
                    del self.connection_priorities[evicted_peer]

            self.active_connections.add(peer_id)
            self.connection_priorities[peer_id] = priority
            heapq.heappush(self._pq, (priority, asyncio.get_event_loop().time(), peer_id))
            return True

    async def remove_peer(self, peer_id: str) -> None:
        async with self._lock:
            if peer_id in self.active_connections:
                self.active_connections.remove(peer_id)
                if peer_id in self.connection_priorities:
                    del self.connection_priorities[peer_id]
                self._pq = [(p, t, pid) for p, t, pid in self._pq if pid != peer_id]
                heapq.heapify(self._pq)
