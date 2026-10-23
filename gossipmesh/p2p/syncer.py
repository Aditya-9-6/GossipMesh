from typing import Any


class VectorClockEntropy:
    pass


class StateSyncer:
    def __init__(self) -> None:
        self.clock = VectorClockEntropy()
