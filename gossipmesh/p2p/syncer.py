from typing import Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class Syncer:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.entropy = VectorClockEntropy()


P2PSyncer = Syncer
