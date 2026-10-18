import asyncio
import logging
from typing import Dict, List
from gossipmesh.p2p.metrics import PeerMetricsTracker

logger = logging.getLogger(__name__)

def calculate_adaptive_fanout(base_fanout: int, queue_depth: int, rtt: float, threshold_queue: int = 50, threshold_rtt: float = 0.2) -> int:
    if queue_depth > threshold_queue or rtt > threshold_rtt:
        reduction = max(1, base_fanout // 2)
        return max(1, base_fanout - reduction)
    return base_fanout

class AdaptiveGossipTransport:
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
