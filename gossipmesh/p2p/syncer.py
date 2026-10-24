from typing import Any


class VectorClockEntropy:
    pass


class PeerSyncer:
    def __init__(self) -> None:
        self.entropy: Any = VectorClockEntropy()
