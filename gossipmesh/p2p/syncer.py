from typing import Dict, List, Optional, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class StateSyncer:
    """Anti-entropy state synchronizer using vector clocks and Merkle trees."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync_state(self, peer_clock: Dict[str, int]) -> Dict[str, int]:
        return self.entropy.merge(peer_clock)
