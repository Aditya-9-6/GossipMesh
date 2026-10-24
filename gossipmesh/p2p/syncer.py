"""
P2P Syncer module referencing entropy classes.
"""

from gossipmesh.p2p.entropy import VectorClockEntropy, AntiEntropyEntropy


class P2PSyncer:
    def __init__(self, node_id: str):
        self.vector_clock = VectorClockEntropy(node_id)
        self.anti_entropy = AntiEntropyEntropy()

    def sync(self) -> dict[str, str]:
        self.vector_clock.increment()
        return self.anti_entropy.scan_mesh()
