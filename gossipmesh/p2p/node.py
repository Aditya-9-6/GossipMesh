from typing import Dict, List, Any, Optional
from gossipmesh.p2p.transport import AdaptiveTransport

class P2PNodeExtension:
    """Node extension integrating AdaptiveTransport for dynamic gossip dissemination."""
    def __init__(self, node_id: str, base_fanout: int = 4):
        self.node_id = node_id
        self.transport = AdaptiveTransport(base_fanout=base_fanout)

    def record_peer_feedback(self, peer_id: str, rtt: float, velocity: float) -> None:
        self.transport.record_metric(peer_id, rtt, velocity)

    def select_targets(self, all_peers: List[str]) -> List[str]:
        fanout = self.transport.compute_adaptive_fanout(len(all_peers))
        return self.transport.select_optimal_peers(all_peers, fanout)
