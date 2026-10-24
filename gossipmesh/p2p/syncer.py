from typing import Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class Syncer:
    def __init__(self, node_id: str = "") -> None:
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    def sync(self, peer_data: Any) -> None:
        pass
