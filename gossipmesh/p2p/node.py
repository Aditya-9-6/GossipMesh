"""P2P Node implementation incorporating entropy-based churn defense and Sybil mitigation."""

import time
import threading
from typing import Dict, Any, Optional, Tuple
from gossipmesh.p2p.health import SlidingWindowPeerHealthScorecard, PeerHealthConfig
from gossipmesh.p2p.churn import MeshChurnManager, ChurnDefenseConfig
from gossipmesh.p2p.pow import mine_pow, verify_pow


class GossipTopic:
    def __init__(self, topic_name: str) -> None:
        self.topic_name = topic_name
        self.subscribers: Set[str] = set()


class PeerNode:
    def __init__(
        self,
        peer_id: str,
        address: str,
        health_config: Optional[PeerHealthConfig] = None,
        churn_config: Optional[ChurnDefenseConfig] = None,
    ) -> None:
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
    def __init__(
        self, health_config: Optional[PeerHealthConfig] = None, churn_config: Optional[ChurnDefenseConfig] = None
    ) -> None:
        self._peers: Dict[str, PeerNode] = {}
        self.health_config = health_config
        self.churn_config = churn_config or ChurnDefenseConfig()
        self.churn_manager = MeshChurnManager(self.churn_config)
        self._lock = threading.Lock()

    def add_peer(self, peer_id: str, address: str) -> PeerNode:
        with self._lock:
            if peer_id not in self._peers:
                self._peers[peer_id] = PeerNode(peer_id, address, self.health_config, self.churn_config)
            return self._peers[peer_id]

    def remove_peer(self, peer_id: str) -> None:
        with self._lock:
            self._peers.pop(peer_id, None)

    def get_peer(self, peer_id: str) -> Optional[PeerNode]:
        with self._lock:
            return self._peers.get(peer_id)

    def record_peer_heartbeat(self, peer_id: str, metadata_vector: Dict[str, int]) -> Tuple[bool, float]:
        """Ingests a heartbeat vector and evaluates entropy-based churn defense."""
        is_sybil, variance = self.churn_manager.process_heartbeat(peer_id, metadata_vector)
        if is_sybil:
            peer = self.get_peer(peer_id)
            if peer:
                peer.record_interaction(latency_ms=0.0, dropped=True, violated=True)
        return is_sybil, variance

    def get_active_peers(self) -> Dict[str, PeerNode]:
        with self._lock:
            active = {}
            for pid, p in self._peers.items():
                if p.is_healthy() and not self.churn_manager.is_peer_quarantined(pid):
                    active[pid] = p
            return active

    def get_all_peer_statuses(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            statuses = {}
            for pid, p in self._peers.items():
                status = p.get_status()
                status["sybil_quarantined"] = self.churn_manager.is_peer_quarantined(pid)
                statuses[pid] = status
            return statuses


class GossipNode:
    def __init__(
        self,
        node_id: str,
        mesh_dir: str,
        public_key: str,
        pow_difficulty: int = 1,
        pow_nonce: Optional[int] = None,
        health_config: Optional[PeerHealthConfig] = None,
        churn_config: Optional[ChurnDefenseConfig] = None,
    ) -> None:
        self.node_id = node_id
        self.mesh_dir = mesh_dir
        self.public_key = public_key
        self.pow_difficulty = pow_difficulty
        if pow_nonce is not None:
            if not verify_pow(public_key, pow_nonce, pow_difficulty):
                raise ValueError("Invalid PoW nonce for given public key and difficulty")
            self.pow_nonce = pow_nonce
        else:
            self.pow_nonce, _ = mine_pow(public_key, pow_difficulty)
        self.peer_manager = PeerManager(health_config, churn_config)
        self.topics: Dict[str, GossipTopic] = {}
