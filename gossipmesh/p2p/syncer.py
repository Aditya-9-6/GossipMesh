"""
P2P Syncer module.
"""

from __future__ import annotations

from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id
        if node_id is not None:
            self.entropy = VectorClockEntropy(node_id)
        else:
            self.entropy = VectorClockEntropy()

    def sync_state(self, peer_vector: dict[str, int]) -> None:
        self.entropy.merge(peer_vector)


class Syncer(P2PSyncer):
    pass
