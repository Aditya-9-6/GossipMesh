"""P2P Transport and PlumTree Multicast layer for GossipMesh."""
import asyncio
import json
from typing import Any, Dict, Set

class PlumTreeMulticast:
    """PlumTree epidemic broadcast multicast implementation with eager and lazy peers."""
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.eager_peers: Set[str] = set()
        self.lazy_peers: Set[str] = set()
        self.lock = asyncio.Lock()

    async def add_eager_peer(self, peer_id: str):
        async with self.lock:
            self.eager_peers.add(peer_id)
            self.lazy_peers.discard(peer_id)

    async def add_lazy_peer(self, peer_id: str):
        async with self.lock:
            if peer_id not in self.eager_peers:
                self.lazy_peers.add(peer_id)

    async def handle_message(self, sender_id: str, message: Dict[str, Any]) -> bool:
        async with self.lock:
            if sender_id in self.eager_peers:
                return True
            return False
