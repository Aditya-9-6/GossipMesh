from typing import Any


class VectorClockEntropy:
    pass


class P2PSyncer:
    def __init__(self, node: Any):
        self.node = node
        self.entropy = VectorClockEntropy()
