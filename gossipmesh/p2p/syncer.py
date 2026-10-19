import logging
from typing import Any, Dict, List, Optional
from gossipmesh.consensus.merkle import MerkleTree

logger = logging.getLogger(__name__)


class VectorClockEntropy:
    """Vector clock entropy tracker for distributed state reconciliation."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.vector_clock: Dict[str, int] = {}

    def increment(self) -> Dict[str, int]:
        self.vector_clock[self.node_id] = self.vector_clock.get(self.node_id, 0) + 1
        return self.vector_clock

    def update(self, other_clock: Dict[str, int]) -> Dict[str, int]:
        for node, ts in other_clock.items():
            self.vector_clock[node] = max(self.vector_clock.get(node, 0), ts)
        self.vector_clock[self.node_id] = self.vector_clock.get(self.node_id, 0) + 1
        return self.vector_clock


class StateSyncer:
    """Anti-entropy state synchronization manager using Merkle trees and Vector Clocks."""

    def __init__(self, node_id: str, state_store: Optional[Dict[str, str]] = None) -> None:
        self.node_id = node_id
        self.state_store = state_store or {}
        self.merkle_tree = MerkleTree(self.state_store)
        self.entropy = VectorClockEntropy(node_id)

    def set_state(self, key: str, value: str) -> None:
        self.state_store[key] = value
        self.merkle_tree.insert(key, value)
        self.entropy.increment()

    def get_root_hash(self) -> str:
        return self.merkle_tree.get_root_hash()

    def reconcile(self, peer_root_hash: str, peer_fingerprints: Dict[str, str]) -> List[str]:
        """Identifies keys that need synchronization based on fingerprint divergence."""
        missing_or_outdated = []
        local_fingerprints = self.merkle_tree.get_subtree_fingerprints()
        for k, v in peer_fingerprints.items():
            if local_fingerprints.get(k) != v:
                missing_or_outdated.append(k)
        return missing_or_outdated
