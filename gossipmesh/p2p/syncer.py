from typing import Dict, Any
from gossipmesh.p2p.entropy import VectorClockEntropy


class StateSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def compute_sync_payload(self) -> Dict[str, Any]:
        return {"node_id": self.node_id, "vector": self.entropy.get_vector()}
