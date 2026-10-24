from __future__ import annotations

from typing import Any, Dict, List, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class StateSyncer:
    def __init__(self, node_id: str, entropy: VectorClockEntropy | None = None) -> None:
        self.node_id = node_id
        self.entropy = entropy or VectorClockEntropy()

    def sync(self, peer_state: Dict[str, Any] | None = None) -> Dict[str, Any] | Any:
        if peer_state is None:
            return True
        return {"status": "synced", "peer": self.node_id}


P2PSyncer = StateSyncer
Syncer = StateSyncer
