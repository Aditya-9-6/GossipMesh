from typing import Dict, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()
        self.entropy_tracker = VectorClockEntropy()

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock) if hasattr(self.entropy_tracker, "update") else None
        return True


class P2PSyncer:
    def __init__(self, entropy: VectorClockEntropy | None = None) -> None:
        self.entropy = entropy or VectorClockEntropy()

    def sync(self) -> Any:
        return True


class Syncer:
    def __init__(self) -> None:
        self.entropy = VectorClockEntropy()
