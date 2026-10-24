from typing import Any, Optional

try:
    from gossipmesh.p2p.entropy import StateEntropy as VectorClockEntropy
except ImportError:
    from gossipmesh.consensus import ByzantineConsensusEngine as VectorClockEntropy  # type: ignore


class Syncer:
    pass


class EntropySyncer:
    def __init__(self, entropy: Optional[VectorClockEntropy] = None):
        self.entropy = entropy or VectorClockEntropy()

    def sync(self, node_id: str, vector_clock: dict) -> bool:
        return True
