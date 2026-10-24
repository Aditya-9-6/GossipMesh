from typing import Any, Dict


class VectorClockEntropy:
    def __init__(self, node_id: str = None) -> None:
        self.node_id = node_id

    def update(self, peer_clock: Dict[str, int]) -> None:
        pass


class P2PSyncer:
    def __init__(self) -> None:
        self.entropy = VectorClockEntropy()


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_tracker = VectorClockEntropy(node_id)

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.update(peer_clock)
        return True
