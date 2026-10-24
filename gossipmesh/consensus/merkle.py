"""
Merkle Tree implementation for state verification and synchronization.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple


def hash_data(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class MerkleNode:
    def __init__(self, hash_value: str, left: Optional[MerkleNode] = None, right: Optional[MerkleNode] = None, key: Optional[str] = None):
        self.hash_value = hash_value
        self.left = left
        self.right = right
        self.key = key


class MerkleTree:
    def __init__(self, items: List[bytes]):
        self.items = items
        self.root = self.build_tree(items)

    def build_tree(self, items: List[bytes]) -> Optional[MerkleNode]:
        if not items:
            return None

        nodes = [MerkleNode(hash_data(item)) for item in items]
        while len(nodes) > 1:
            next_level: List[MerkleNode] = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else left
                combined_hash = hash_data((left.hash_value + right.hash_value).encode("utf-8"))
                next_level.append(MerkleNode(combined_hash, left, right))
            nodes = next_level

        return nodes[0]

    def get_root_hash(self) -> Optional[str]:
        return self.root.hash_value if self.root else None

    def get_fingerprints(self) -> Dict[str, str]:
        fingerprints: Dict[str, str] = {}

        def _traverse(node: Optional[MerkleNode], prefix: str):
            if not node:
                return
            fingerprints[prefix] = node.hash_value
            if node.left:
                _traverse(node.left, prefix + "0")
            if node.right:
                _traverse(node.right, prefix + "1")

        _traverse(self.root, "")
        return fingerprints

    def get_subtree_fingerprints(self) -> Dict[str, str]:
        """Returns all subtree keys and their respective fingerprints."""
        fingerprints: Dict[str, str] = {}
        if not self.root:
            return fingerprints
        queue = [(self.root, "root")]
        while queue:
            node, path = queue.pop(0)
            if getattr(node, "key", None):
                fingerprints[node.key] = node.hash_value
            if node.left:
                queue.append((node.left, path + "0"))
            if node.right:
                queue.append((node.right, path + "1"))
        return fingerprints
