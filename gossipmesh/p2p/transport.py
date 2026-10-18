import time
import math
from typing import Dict, List, Optional, Tuple

class AdaptiveTransport:
    """
    Adaptive gossip transport layer that monitors round-trip times (RTT) and message
    propagation velocities to dynamically adjust fanout and prune high-latency or unresponsive nodes.
    """
    def __init__(self, base_fanout: int = 4, target_prob: float = 0.99, max_rtt_threshold: float = 2.0):
        self.base_fanout = base_fanout
        self.target_prob = target_prob
        self.max_rtt_threshold = max_rtt_threshold
        self.peer_metrics: Dict[str, Dict[str, float]] = {}

    def record_metric(self, peer_id: str, rtt: float, velocity: float) -> None:
        """Records or updates RTT and velocity metrics for a specific peer."""
        self.peer_metrics[peer_id] = {
            "rtt": rtt,
            "velocity": velocity,
            "last_updated": time.time()
        }

    def compute_adaptive_fanout(self, total_peers: int) -> int:
        """Computes adaptive fanout size maintaining probabilistic dissemination bounds."""
        if total_peers <= 1:
            return max(1, total_peers)
        
        # Standard epidemic dissemination probability model: 1 - (1 - k/N)^t >= p
        active_peers = len([p for p, m in self.peer_metrics.items() if m["rtt"] <= self.max_rtt_threshold])
        effective_peers = max(1, active_peers if active_peers > 0 else total_peers)
        
        # Compute optimal fanout based on target probability
        fanout = math.ceil(math.log(1.0 - self.target_prob) / math.log(max(0.001, 1.0 - (1.0 / effective_peers))))
        return max(1, min(fanout, effective_peers, self.base_fanout * 2))

    def select_optimal_peers(self, peers: List[str], count: int) -> List[str]:
        """Selects top peers prioritizing lowest RTT and highest propagation velocity."""
        if not peers:
            return []
            
        scored_peers = []
        for peer in peers:
            metrics = self.peer_metrics.get(peer, {"rtt": 0.1, "velocity": 1.0, "last_updated": time.time()})
            if metrics["rtt"] > self.max_rtt_threshold:
                continue  # Prune unresponsive/high-latency node
            score = (1.0 / (metrics["rtt"] + 0.001)) * metrics["velocity"]
            scored_peers.append((score, peer))
            
        scored_peers.sort(key=lambda x: x[0], reverse=True)
        selected = [p for _, p in scored_peers[:count]]
        
        # Fallback if too many pruned
        if not selected and peers:
            return peers[:min(len(peers), count)]
            
        return selected
