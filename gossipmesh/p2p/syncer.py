from typing import Any, Dict, List, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self, node_id: Optional[str] = None, entropy: VectorClockEntropy | None = None) -> None:
        self.node_id = node_id
        self.entropy = entropy or VectorClockEntropy()

    def sync_state(self, peer_state: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "synced", "node_id": self.node_id}

    def sync(self, peer_data: Any = None) -> Any:
        return True


Syncer = P2PSyncer
