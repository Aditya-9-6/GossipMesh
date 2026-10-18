import random
from typing import List, Dict, Any
from gossipmesh.p2p.metrics import PeerMetricsRegistry

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
            # Score formula: lower score means higher priority. Lower RTT and fewer failures are preferred.
            score = smoothed_rtt * (1.0 + failures * 2.0)
            scored_peers.append((score, peer))

        scored_peers.sort(key=lambda x: x[0])
        selected = [peer for _, peer in scored_peers[:fanout]]
        return selected
