from __future__ import annotations
from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    """P2P node state synchronization engine using vector clock entropy."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync_state(self, peer_clock: dict[str, int]) -> float:
        self.entropy.merge(peer_clock)
        return self.entropy.compute_entropy()
