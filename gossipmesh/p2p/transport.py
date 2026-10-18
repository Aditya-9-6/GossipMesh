from typing import Dict, Any, List
from gossipmesh.p2p.fanout import AdaptiveFanoutController

class GossipTransport:
    def __init__(self, base_fanout: int = 4):
        self.fanout_controller = AdaptiveFanoutController(base_fanout=base_fanout)
        self.peers: List[str] = []

    def get_adaptive_fanout(self, latency_ms: float, churn_rate: float) -> int:
        """Calculates target peer dissemination breadth using the adaptive fanout controller."""
        return self.fanout_controller.compute_fanout(
            network_latency_ms=latency_ms,
            peer_churn_rate=churn_rate,
            total_peers=len(self.peers)
        )
