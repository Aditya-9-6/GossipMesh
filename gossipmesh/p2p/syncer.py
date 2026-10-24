from typing import Dict, List, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class VectorClockEntropy:
    pass


class StateSyncer:
    def __init__(self, node_id: str = "") -> None:
        self.node_id = node_id
        self.clock = VectorClockEntropy()
        self.entropy_tracker = VectorClockEntropy(node_id) if node_id else self.clock

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        if hasattr(self.entropy_tracker, "update") and callable(getattr(self.entropy_tracker, "update")):
            self.entropy_tracker.update(peer_clock)
        return True


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_tracker = VectorClockEntropy(node_id)

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock)
        return True
