"""
Merkle Tree implementation for state verification and synchronization.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional


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
        self.root = self._build_level(nodes)

    def _build_level(self, nodes: List[MerkleNode]) -> MerkleNode:
        if len(nodes) == 1:
            return nodes[0]
        next_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            parent_hash = hash_pair(left.hash_value, right.hash_value)
            parent = MerkleNode(hash_value=parent_hash, left=left, right=right)
            next_level.append(parent)
        return self._build_level(next_level)

    def get_root_hash(self) -> str:
        return self.root.hash_value if self.root else hash_data("")
