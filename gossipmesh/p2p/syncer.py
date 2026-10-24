from typing import List, Dict, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_calculator = VectorClockEntropy(node_id)
        self.entropy_tracker = self.entropy_calculator

    def evaluate_sync_urgency(self, peer_clocks: List[Dict[str, int]]) -> float:
        return self.entropy_calculator.compute_entropy(peer_clocks)

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock)
        return True
