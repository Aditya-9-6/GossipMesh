from typing import Any, Dict, List, Optional
import logging

from gossipmesh.p2p.entropy import VectorClockEntropyCalculator as VectorClockEntropy

logger = logging.getLogger(__name__)


class VectorClockSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_calculator = VectorClockEntropy()

    def sync(self, peer_clock: Dict[str, int]) -> Dict[str, Any]:
        return {"status": "synced", "node_id": self.node_id}


class Syncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    def sync(self, peer_data: Any) -> None:
        pass
