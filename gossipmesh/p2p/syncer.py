from typing import Dict, List, Any
from gossipmesh.p2p.entropy import AntiEntropyEntropy

VectorClockEntropy = AntiEntropyEntropy


class PeerSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy_tracker = VectorClockEntropy()

    def sync_state(self, peer_clock: Dict[str, int]) -> bool:
        self.entropy_tracker.scan_mesh(list(peer_clock.keys()))
        return True
