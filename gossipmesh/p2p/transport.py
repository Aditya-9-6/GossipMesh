import random
import logging
from typing import List, Dict, Any
from gossipmesh.p2p.metrics import PeerMetricsRegistry, PeerMetricsTracker

logger = logging.getLogger(__name__)

def calculate_adaptive_fanout(base_fanout: int, queue_depth: int, rtt: float, threshold_queue: int = 50, threshold_rtt: float = 0.2) -> int:
    if queue_depth > threshold_queue or rtt > threshold_rtt:
        reduction = max(1, base_fanout // 2)
        return max(1, base_fanout - reduction)
    return base_fanout

class AdaptiveTransport:
    """Handles adaptive P2P gossip fanout and peer pruning based on latency metrics."""
    def __init__(self, metrics_registry: PeerMetricsRegistry, base_fanout: int = 4):
        self.metrics_registry = metrics_registry
        self.base_fanout = base_fanout

    def calculate_fanout(self, peer_count: int, congestion_signal: float = 0.0) -> int:
        """Calculates dynamic fanout based on total peers and global congestion."""
        if peer_count <= 0:
            return 1
        effective_fanout = int(self.base_fanout * (1.0 - min(max(congestion_signal, 0.0), 1.0)))
        return max(1, min(effective_fanout, peer_count))

    def select_peers(self, all_peers: List[str], congestion_signal: float = 0.0) -> List[str]:
        """Selects subset of peers to propagate gossip messages to using latency-aware scoring."""
        if not all_peers:
            return []

        fanout = self.calculate_fanout(len(all_peers), congestion_signal)
        if fanout >= len(all_peers):
            return list(all_peers)

        scored_peers = []
        for peer in all_peers:
            smoothed_rtt, failures = self.metrics_registry.get_metrics(peer)
            score = (smoothed_rtt * (1.0 + failures * 2.0))
            scored_peers.append((score, peer))

        scored_peers.sort(key=lambda x: x[0])
        selected = [peer for _, peer in scored_peers[:fanout]]
        return selected

class AdaptiveGossipTransport:
    """Transport supporting backpressure-aware adaptive gossip distribution."""
    def __init__(self, base_fanout: int = 8, threshold_queue: int = 50, threshold_rtt: float = 0.2):
        self.base_fanout = base_fanout
        self.threshold_queue = threshold_queue
        self.threshold_rtt = threshold_rtt
        self.metrics_tracker = PeerMetricsTracker()
        self.peer_connections: Dict[str, bool] = {}

    def register_peer(self, peer_id: str):
        self.peer_connections[peer_id] = True

    def record_peer_telemetry(self, peer_id: str, queue_depth: int, rtt: float):
        self.metrics_tracker.update_queue_depth(peer_id, queue_depth)
        self.metrics_tracker.update_rtt(peer_id, rtt)

    def get_effective_fanout(self, peer_id: str) -> int:
        q_depth = self.metrics_tracker.get_queue_depth(peer_id)
        rtt = self.metrics_tracker.get_rtt(peer_id)
        return calculate_adaptive_fanout(
            self.base_fanout, q_depth, rtt, self.threshold_queue, self.threshold_rtt
        )

    async def send_gossip(self, peer_id: str, payload: dict) -> bool:
        if not self.peer_connections.get(peer_id, False):
            return False
        fanout = self.get_effective_fanout(peer_id)
        logger.debug(f"Sending gossip to peer {peer_id} with effective fanout {fanout}")
        return True
