from typing import Any, Dict, List
from gossipmesh.p2p.entropy import VectorClockEntropy


class StateSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        return self.entropy.compare(peer_clock)
