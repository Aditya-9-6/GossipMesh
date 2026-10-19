from typing import Dict, Any, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    """Synchronizes P2P state across nodes using entropy and vector clocks."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_calculator = VectorClockEntropy(node_id)

    def evaluate_sync_priority(self, local_clock: Dict[str, int], remote_clock: Dict[str, int]) -> float:
        """Evaluates synchronization priority based on clock divergence entropy."""
        return self.entropy_calculator.compute_divergence(local_clock, remote_clock)
