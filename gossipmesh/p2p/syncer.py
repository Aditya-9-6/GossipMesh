from typing import Any, Dict, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class PeerSyncer:
    """Handles peer synchronization and vector clock entropy exchanges."""

    def __init__(self, node_id: str, max_epochs: int = 1024):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id, max_epochs=max_epochs)

    def sync_clock(self, remote_clock: Dict[str, int]) -> None:
        self.entropy.update(remote_clock)
