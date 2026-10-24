from typing import Any
from gossipmesh.p2p.entropy import StateEntropy, VectorClockEntropy


class P2PSyncer:
    def __init__(self, entropy: VectorClockEntropy | None = None) -> None:
        self.entropy = entropy or VectorClockEntropy()

    def sync(self) -> Any:
        return True


Syncer = P2PSyncer
