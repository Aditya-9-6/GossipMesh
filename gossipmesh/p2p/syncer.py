from typing import Dict, Any, Optional
import logging

from gossipmesh.p2p.entropy import VectorClockEntropy

logger = logging.getLogger(__name__)


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync_state(self, peer_id: str, peer_clock: Dict[str, int]) -> Dict[str, Any]:
        divergence = self.entropy.compare(peer_clock)
        return {
            "node_id": self.node_id,
            "peer_id": peer_id,
            "divergence": divergence,
        }
