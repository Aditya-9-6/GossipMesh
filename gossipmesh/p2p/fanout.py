from typing import Dict, Any, Optional
from gossipmesh.p2p.matrix import EpidemicReachabilityMatrix


class DynamicFanoutController:
    """Computes localized message spread efficiency and adjusts node-specific
    dissemination fanout without causing flooding storms."""

    def __init__(self, node_id: str, base_fanout: int = 4, min_fanout: int = 1, max_fanout: int = 12) -> None:
        self.node_id = node_id
        self.base_fanout = base_fanout
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout
        self.matrix = EpidemicReachabilityMatrix(node_id)

    def compute_fanout(self) -> int:
        avg_reach = self.matrix.average_reachability()
        # If average reachability is high, we reduce fanout to save bandwidth;
        # if low, we increase fanout to ensure epidemic propagation.
        adjustment = int((0.5 - avg_reach) * 4)
        computed = self.base_fanout + adjustment
        return max(self.min_fanout, min(self.max_fanout, computed))

    def update_peer_feedback(self, peer_id: str, success: bool) -> None:
        self.matrix.record_ack(peer_id, success)

    get_metrics = lambda self: {
        "node_id": self.node_id,
        "current_fanout": self.compute_fanout(),
        "matrix": self.matrix.to_dict(),
    }
