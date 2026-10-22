"""P2P Mesh State Synchronization engine."""

from typing import Dict, Any, Optional
from gossipmesh.p2p.entropy import VectorClock


class StateSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id)

    def sync_state(self, peer_state: Dict[str, Any]) -> Dict[str, Any]:
        peer_vc = peer_state.get("vector_clock", {})
        self.vector_clock.merge(peer_vc)
        return {"node_id": self.node_id, "vector_clock": self.vector_clock.to_dict(), "status": "synchronized"}
