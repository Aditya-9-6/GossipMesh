import time
import asyncio
from typing import Dict, Set, Optional, Any
from collections import OrderedDict

class BoundedLRUCache:
    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self._cache: OrderedDict[str, float] = OrderedDict()

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def add(self, key: str) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.capacity:
                self._cache.popitem(last=False)
            self._cache[key] = time.time()

    def clear(self) -> None:
        self._cache.clear()

class PlumTreeMulticast:
    def __init__(self, node_id: str, cache_capacity: int = 10000):
        self.node_id = node_id
        self.eager_peers: Set[str] = set()
        self.lazy_peers: Set[str] = set()
        self.seen_messages = BoundedLRUCache(capacity=cache_capacity)
        self._lock = asyncio.Lock()

    async def add_peer(self, peer_id: str, eager: bool = True) -> None:
        async with self._lock:
            if eager:
                self.eager_peers.add(peer_id)
                self.lazy_peers.discard(peer_id)
            else:
                self.lazy_peers.add(peer_id)
                self.eager_peers.discard(peer_id)

    async def remove_peer(self, peer_id: str) -> None:
        async with self._lock:
            self.eager_peers.discard(peer_id)
            self.lazy_peers.discard(peer_id)

    async def handle_message(self, msg_id: str, sender_id: str) -> Dict[str, Any]:
        async with self._lock:
            if msg_id in self.seen_messages:
                if sender_id in self.eager_peers:
                    self.eager_peers.remove(sender_id)
                    self.lazy_peers.add(sender_id)
                    return {"action": "prune", "peer": sender_id}
                return {"action": "ignore"}
            
            self.seen_messages.add(msg_id)
            return {"action": "deliver", "forward_eager": list(self.eager_peers - {sender_id}), "notify_lazy": list(self.lazy_peers - {sender_id})}

    async def graft(self, peer_id: str) -> None:
        async with self._lock:
            self.lazy_peers.discard(peer_id)
            self.eager_peers.add(peer_id)
