import asyncio
from typing import Dict, List, Tuple
from gossipmesh.p2p.rate_limiter import TokenBucketRateLimiter

class P2PConnectionManager:
    def __init__(self, max_connections: int = 50, rate_limiter: TokenBucketRateLimiter = None):
        self.max_connections = max_connections
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter()
        self.active_connections: Dict[str, asyncio.StreamWriter] = {}
        self.peer_priorities: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def admit_connection(self, peer_id: str, priority: int = 0) -> bool:
        async with self._lock:
            allowed = await self.rate_limiter.acquire(peer_id)
            if not allowed:
                return False
            if len(self.active_connections) >= self.max_connections:
                if not self.active_connections:
                    return False
                lowest_peer = min(self.peer_priorities.items(), key=lambda x: x[1])
                if priority <= lowest_peer[1]:
                    return False
                await self.drop_connection(lowest_peer[0])
            return True

    async def register_connection(self, peer_id: str, writer: asyncio.StreamWriter, priority: int = 0):
        async with self._lock:
            self.active_connections[peer_id] = writer
            self.peer_priorities[peer_id] = priority

    async def drop_connection(self, peer_id: str):
        writer = self.active_connections.pop(peer_id, None)
        self.peer_priorities.pop(peer_id, None)
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
