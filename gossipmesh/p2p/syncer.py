"""
P2P Syncer module.
"""

from __future__ import annotations

from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self, entropy: VectorClockEntropy | None = None) -> None:
        self.entropy = entropy or VectorClockEntropy()

    def sync(self) -> None:
        pass


class Syncer:
    pass
