from typing import Dict, List, Set, Tuple
from gossipmesh.consensus.merkle import MerkleTree


class MerkleSyncer:
    """Anti-entropy synchronization engine using Merkle trees."""

    def __init__(self, local_tree: MerkleTree):
        self.local_tree = local_tree

    def get_sync_manifest(self) -> Dict[str, str]:
        """Generates a manifest of subtree fingerprints for peer exchange."""
        return self.local_tree.get_subtree_fingerprints()

    def reconcile(self, peer_manifest: Dict[str, str]) -> List[str]:
        """Compares peer manifest with local items and identifies divergent keys.
        Restricts full payloads to divergent leaf nodes.
        """
        local_manifest = self.local_tree.get_subtree_fingerprints()
        divergent_keys: Set[str] = set()

        all_keys = set(local_manifest.keys()).union(set(peer_manifest.keys()))
        for key in all_keys:
            local_hash = local_manifest.get(key)
            peer_hash = peer_manifest.get(key)
            if local_hash != peer_hash:
                divergent_keys.add(key)

        return sorted(list(divergent_keys))

    def generate_delta_payload(self, divergent_keys: List[str]) -> Dict[str, str]:
        """Pulls state values exclusively for divergent keys to minimize bandwidth."""
        delta = {}
        for key in divergent_keys:
            if key in self.local_tree.items:
                delta[key] = self.local_tree.items[key]
        return delta
