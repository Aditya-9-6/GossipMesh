from typing import Dict, Any, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class PeerSyncer:
    """Handles peer synchronization using vector clock entropy reconciliation."""

    def __init__(self, node_id: str, max_epochs: int = 1024):
        self.node_id = node_id
        self.entropy_tracker = VectorClockEntropy(node_id, max_epochs=max_epochs)

    def sync_clock(self, remote_node: str, remote_clock: Dict[str, int]) -> None:
        self.entropy_tracker.update(remote_clock)

    def get_entropy(self) -> Dict[str, int]:
        return dict(self.entropy_tracker.clock)
