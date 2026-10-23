import time
import threading
from typing import Dict, Any, Optional
from gossipmesh.p2p.health import SlidingWindowPeerHealthScorecard, PeerHealthConfig


class PeerNode:
    def __init__(self, peer_id: str, address: str, health_config: Optional[PeerHealthConfig] = None) -> None:
        self.peer_id = peer_id
        self.address = address
        self.scorecard = SlidingWindowPeerHealthScorecard(health_config)
        self.connected_at = time.time()
        self._lock = threading.Lock()

    def record_interaction(self, latency_ms: float, dropped: bool = False, violated: bool = False) -> float:
        return self.scorecard.record_sample(latency_ms, dropped, violated)

    def is_healthy(self) -> bool:
        metrics = self.scorecard.get_metrics()
        return not metrics["is_quarantined"]

    def get_status(self) -> Dict[str, Any]:
        metrics = self.scorecard.get_metrics()
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "connected_at": self.connected_at,
            **metrics,
        }


class PeerManager:
    def __init__(self, health_config: Optional[PeerHealthConfig] = None) -> None:
        self._peers: Dict[str, PeerNode] = {}
        self.health_config = health_config
        self._lock = threading.Lock()

    def add_peer(self, peer_id: str, address: str) -> PeerNode:
        with self._lock:
            if peer_id not in self._peers:
                self._peers[peer_id] = PeerNode(peer_id, address, self.health_config)
            return self._peers[peer_id]

    def remove_peer(self, peer_id: str) -> None:
        with self._lock:
            self._peers.pop(peer_id, None)

    def get_peer(self, peer_id: str) -> Optional[PeerNode]:
        with self._lock:
            return self._peers.get(peer_id)

    def get_active_peers(self) -> Dict[str, PeerNode]:
        with self._lock:
            return {pid: p for pid, p in self._peers.items() if p.is_healthy()}

    def get_all_peer_statuses(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {pid: p.get_status() for pid, p in self._peers.items()}
