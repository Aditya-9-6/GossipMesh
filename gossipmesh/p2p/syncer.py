from typing import Any, Dict
from gossipmesh.p2p.entropy import VectorClockEntropy


class VectorClockEntropy:
    def __init__(self) -> None:
        pass


class ClockSyncer:
    def __init__(self):
        pass

    def calculate(self, clocks: list[Dict[str, int]]) -> float:
        return 0.0


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_tracker = VectorClockEntropy()

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        return True


class Syncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    def sync(self, peer_data: Any) -> None:
        pass
