import math
from typing import Dict, Any, Optional
from gossipmesh.p2p.matrix import EpidemicReachabilityMatrix

class AdaptiveFanoutController:
    def __init__(self, base_fanout: int = 4, min_fanout: int = 2, max_fanout: int = 16):
        self.base_fanout = base_fanout
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout

    def compute_fanout(self, network_latency_ms: float, peer_churn_rate: float, total_peers: int) -> int:
        """Dynamically computes the adaptive fanout based on network latency, peer churn, and total peers."""
        if total_peers <= 0:
            return self.min_fanout
        
        churn_factor = 1.0 + min(max(peer_churn_rate, 0.0), 1.0)
        latency_factor = 1.0 + min(max(network_latency_ms / 1000.0, 0.0), 2.0)
        
        dynamic_target = float(self.base_fanout) * churn_factor * latency_factor
        log_scale = math.log2(max(total_peers, 2))
        
        computed = int(round(dynamic_target * (1.0 + 0.1 * log_scale)))
        return max(self.min_fanout, min(self.max_fanout, computed))


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

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "current_fanout": self.compute_fanout(),
            "matrix": self.matrix.to_dict()
        }
