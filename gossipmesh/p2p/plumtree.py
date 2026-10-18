import time
import logging
from typing import Dict, Set, List, Optional, Any

logger = logging.getLogger(__name__)

class PlumTreePeer:
    def __init__(self, peer_id: str):
        self.peer_id = peer_id
        self.last_seen = time.time()

class PlumTreeMessage:
    def __init__(self, message_id: str, payload: Any, source_id: str):
        self.message_id = message_id
        self.payload = payload
        self.source_id = source_id
        self.timestamp = time.time()

class PlumTreeMesh:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.eager_peers: Set[str] = set()
        self.lazy_peers: Set[str] = set()
        self.seen_messages: Dict[str, float] = {}
        self.message_history: Dict[str, Any] = {}

    def add_eager_peer(self, peer_id: str) -> None:
        self.eager_peers.add(peer_id)
        self.lazy_peers.discard(peer_id)

    def add_lazy_peer(self, peer_id: str) -> None:
        if peer_id not in self.eager_peers:
            self.lazy_peers.add(peer_id)

    def remove_peer(self, peer_id: str) -> None:
        self.eager_peers.discard(peer_id)
        self.lazy_peers.discard(peer_id)

    def handle_message(self, message_id: str, payload: Any, from_peer: str) -> bool:
        if message_id in self.seen_messages:
            # Duplicate delivery detected: transition peer from eager to lazy if needed
            if from_peer in self.eager_peers:
                self.eager_peers.remove(from_peer)
                self.lazy_peers.add(from_peer)
            return True

        self.seen_messages[message_id] = time.time()
        self.message_history[message_id] = payload

        # If received from a lazy peer, graft back to eager
        if from_peer in self.lazy_peers:
            self.lazy_peers.remove(from_peer)
            self.eager_peers.add(from_peer)

        return False

    def get_eager_peers(self) -> List[str]:
        return list(self.eager_peers)

    def get_lazy_peers(self) -> List[str]:
        return list(self.lazy_peers)
