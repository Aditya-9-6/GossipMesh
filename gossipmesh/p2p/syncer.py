from typing import Dict, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class VectorClockEntropy:
    def __init__(self, node_id: str = "") -> None:
        self.node_id = node_id


class PeerSyncer:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.entropy: Any = VectorClockEntropy(node_id)
        self.entropy_tracker = self.entropy

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock)
        return True
