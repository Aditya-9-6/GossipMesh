from typing import List, Dict, Any
from gossipmesh.p2p.metrics import PeerMetricsTracker
from gossipmesh.p2p.fanout import AdaptiveFanoutController

class AdaptiveTransport:
    """Adaptive gossip transport layer featuring latency-aware epidemic fanout adjustment.
    """
    def __init__(self, base_fanout: int = 5, min_fanout: int = 1, max_fanout: int = 15, stale_threshold: float = 60.0):
        self.base_fanout = base_fanout
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout
        self.metrics = PeerMetricsTracker(stale_threshold_sec=stale_threshold)

    def calculate_fanout(self, peer_id: str, current_congestion: float = 0.0) -> int:
        rtt = self.metrics.get_rtt(peer_id)
        if rtt == 0.0:
            return self.base_fanout
        
        # Inverse scaling: higher RTT or congestion decreases fanout breadth
        adjustment = int(rtt * 10.0 + current_congestion * 5.0)
        computed = self.base_fanout - adjustment
        return max(self.min_fanout, min(self.max_fanout, computed))

    def select_peers(self, all_peers: List[str], current_congestion: float = 0.0) -> List[str]:
        if not all_peers:
            return []
        # Select peers based on lowest RTT first or fallback to base fanout count
        sorted_peers = sorted(
            all_peers,
            key=lambda p: (self.metrics.get_rtt(p) == 0.0, self.metrics.get_rtt(p))
        )
        target_count = max(self.min_fanout, min(len(all_peers), self.base_fanout))
        return sorted_peers[:target_count]


class GossipTransport:
    """Transport wrapper for GossipMesh integrating the AdaptiveFanoutController."""
    def __init__(self, base_fanout: int = 4, min_fanout: int = 2, max_fanout: int = 16):
        self.fanout_controller = AdaptiveFanoutController(
            base_fanout=base_fanout,
            min_fanout=min_fanout,
            max_fanout=max_fanout
        )
        self.peers: List[str] = []

    def get_adaptive_fanout(self, latency_ms: float, churn_rate: float) -> int:
        """Calculates target peer dissemination breadth using the adaptive fanout controller."""
        return self.fanout_controller.compute_fanout(
            network_latency_ms=latency_ms,
            peer_churn_rate=churn_rate,
            total_peers=len(self.peers)
        )
