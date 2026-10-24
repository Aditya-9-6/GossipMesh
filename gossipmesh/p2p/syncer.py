from gossipmesh.p2p.entropy import VectorClockEntropy
from typing import Any


class PeerSyncer:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.entropy = VectorClockEntropy()
