from __future__ import annotations
from gossipmesh.p2p.entropy import VectorClockEntropy


class Syncer:
    def __init__(self) -> None:
        self.entropy = VectorClockEntropy()
