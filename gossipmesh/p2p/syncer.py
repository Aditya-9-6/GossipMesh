from typing import Dict, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class VectorClockSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync(self, peer_clock: Dict[str, int]) -> None:
        self.entropy.update(peer_clock)

    def get_score(self) -> float:
        return self.entropy.get_entropy_score()
