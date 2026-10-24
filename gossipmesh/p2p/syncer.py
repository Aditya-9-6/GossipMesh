from typing import Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class VectorClockEntropy:
    def __init__(self) -> None:
        pass


class Syncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    def sync(self, peer_data: Any) -> None:
        pass
