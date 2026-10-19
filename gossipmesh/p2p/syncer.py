from typing import Dict, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class StateSyncer:
    """Synchronizes state across nodes using vector clock entropy."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_calculator = VectorClockEntropy(node_id)

    def evaluate_divergence(self, local_clock: Dict[str, int], remote_clock: Dict[str, int]) -> float:
        return self.entropy_calculator.calculate(local_clock, remote_clock)
