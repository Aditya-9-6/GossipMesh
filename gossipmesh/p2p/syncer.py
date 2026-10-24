"""
P2P Node State Syncer.
"""

from typing import Dict, Any, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class StateSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.vector_clock = VectorClockEntropy(node_id)

    def sync(self, peer_state: Dict[str, Any]) -> None:
        self.vector_clock.update(peer_state.get("vector_clock", {}))
