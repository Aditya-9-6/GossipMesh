"""
Merkle Tree implementation for state verification and synchronization.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple


def hash_data(data: str | bytes) -> str:
    if isinstance(data, str):
        data_bytes = data.encode("utf-8")
    else:
        data_bytes = data
    return hashlib.sha256(data_bytes).hexdigest()


def hash_pair(left: str, right: str) -> str:
    combined = left + right
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class MerkleNode:
    def __init__(
        self,
        hash_value: str,
        left: Optional[MerkleNode] = None,
        right: Optional[MerkleNode] = None,
        key: Optional[str] = None,
    ):
        self.hash_value = hash_value
        self.left = left
        self.right = right
        self.key = key


class MerkleTree:
    def __init__(self, items: Optional[Dict[str, str]] = None):
        self.root: Optional[MerkleNode] = None
        self.items: Dict[str, str] = {}
        if items:
            for k, v in items.items():
                if k is not None:
                    self.insert(k, v)

    def insert(self, key: str, value: str) -> None:
        self.items[key] = value
        self._rebuild()

    def _rebuild(self) -> None:
        sorted_keys = sorted(self.items.keys())
        nodes: List[MerkleNode] = [MerkleNode(hash_value=hash_data(k + self.items[k]), key=k) for k in sorted_keys]
        if not nodes:
            self.root = None
            return

        while len(nodes) > 1:
            parent_level: List[MerkleNode] = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                if i + 1 < len(nodes):
                    right = nodes[i + 1]
                    parent_hash = hash_pair(left.hash_value, right.hash_value)
                    parent_level.append(MerkleNode(hash_value=parent_hash, left=left, right=right))
                else:
                    parent_level.append(left)
            nodes = parent_level
        self.root = nodes[0]

    def get_root_hash(self) -> Optional[str]:
        return self.root.hash_value if self.root else None

    def get_proof(self, key: str) -> List[Tuple[str, str]]:
        if key not in self.items or not self.root:
            return []
        proof: List[Tuple[str, str]] = []

        def _find(node: Optional[MerkleNode], target_key: str) -> bool:
            if not node:
                return False
            if node.key == target_key:
                return True
            if node.left and _find(node.left, target_key):
                if node.right:
                    proof.append(("right", node.right.hash_value))
                return True
            if node.right and _find(node.right, target_key):
                if node.left:
                    proof.append(("left", node.left.hash_value))
                return True
            return False

        _find(self.root, key)
        return proof
