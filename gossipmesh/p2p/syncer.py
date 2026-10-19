from typing import Dict, Any, List
from gossipmesh.p2p.entropy import VectorClockEntropy


class AntiEntropySyncer:
    """Handles anti-entropy state synchronization between GossipMesh peers."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def prepare_sync_payload(self) -> Dict[str, Any]:
        self.entropy.increment()
        return {
            "node_id": self.node_id,
            "vector_clock": self.entropy.to_dict(),
        }

    def reconcile(self, remote_payload: Dict[str, Any]) -> int:
        remote_clock = remote_payload.get("vector_clock", {})
        divergence = self.entropy.compute_divergence(remote_clock)
        self.entropy.update(remote_clock)
        return divergence
