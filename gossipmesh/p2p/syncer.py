from __future__ import annotations
from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync(self, peer_vector: dict[str, int]) -> float:
        return self.entropy.compute_entropy(peer_vector)
