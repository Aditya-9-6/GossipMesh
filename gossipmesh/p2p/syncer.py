from typing import Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class VectorClockEntropy:
    def __init__(self) -> None:
        pass


class P2PSyncer:
    def __init__(self) -> None:
        self.entropy = VectorClockEntropy()
