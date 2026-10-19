from typing import Dict, List, Optional

try:
    from gossipmesh.p2p.entropy import VectorClock
except ImportError:

    class VectorClock:
        def __init__(self, node_id: str):
            self.node_id = node_id
            self.clock: Dict[str, int] = {node_id: 0}

        def increment(self) -> None:
            self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1


from gossipmesh.consensus.merkle import MerkleTree


class AntiEntropySyncer:
    """Anti-entropy synchronization engine using Merkle trees and vector clocks."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.merkle_tree = MerkleTree()
        self.vector_clock = VectorClock(node_id)

    def update_state(self, key: str, value: str) -> None:
        self.merkle_tree.insert(key, value)
        self.vector_clock.increment()

    def get_root_hash(self) -> str:
        return self.merkle_tree.get_root_hash()

    def compare_and_sync(self, peer_fingerprints: Dict[str, str]) -> List[str]:
        local_fingerprints = self.merkle_tree.get_subtree_fingerprints()
        diff_keys = []
        for key, hsh in peer_fingerprints.items():
            if local_fingerprints.get(key) != hsh:
                diff_keys.append(key)
        for key, hsh in local_fingerprints.items():
            if key not in peer_fingerprints:
                diff_keys.append(key)
        return diff_keys
