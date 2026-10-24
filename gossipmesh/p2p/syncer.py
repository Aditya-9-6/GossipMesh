from typing import List, Dict, Any
from gossipmesh.p2p.entropy import VectorClockEntropy as BaseVectorClockEntropy


class VectorClockEntropy:
    def increment(self, *args, **kwargs):
        pass


class AntiEntropyEntropy:
    def scan_mesh(self, *args, **kwargs):
        pass


class P2PSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_calculator = BaseVectorClockEntropy(node_id)
        self.entropy_tracker = self.entropy_calculator
        self.entropy = self.entropy_calculator

    def evaluate_sync_urgency(self, peer_clocks: List[Dict[str, int]]) -> float:
        return self.entropy_calculator.compute_entropy(peer_clocks)

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock)
        return True

    def sync(self, peer_data: Any) -> None:
        if isinstance(peer_data, list):
            self.evaluate_sync_urgency(peer_data)
        elif isinstance(peer_data, dict):
            self.sync_state(peer_data)


class Syncer(P2PSyncer):
    pass
