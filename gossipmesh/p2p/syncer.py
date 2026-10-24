"""
P2P Syncer for anti-entropy replication and state synchronization.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync_state(self, peer_state: Dict[str, Any]) -> Dict[str, Any]:
        remote_clock = peer_state.get("vector_clock", {})
        self.entropy.merge(remote_clock)
        return {"status": "synchronized", "node_id": self.node_id, "clock": self.entropy.clock}
