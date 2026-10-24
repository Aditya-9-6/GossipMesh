from typing import Any
from gossipmesh.p2p.entropy import StateEntropy, VectorClockEntropy


class Syncer:
    def __init__(self) -> None:
        self.entropy = VectorClockEntropy()
