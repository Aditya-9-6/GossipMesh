from typing import Dict, List, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class ClockSyncer:
    def __init__(self):
        pass

    def calculate(self, clocks: list[Dict[str, int]]) -> float:
        return 0.0


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_tracker = VectorClockEntropy(node_id)

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock)
        return True
