from gossipmesh.p2p.entropy import VectorClockEntropy
from typing import Dict, Any, List, Optional


class PeerSyncer:
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    def sync_state(self, peer_state: Dict[str, Any]) -> Dict[str, Any]:
        return self.entropy.compare(peer_state)
