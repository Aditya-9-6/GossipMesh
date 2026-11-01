from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

try:
    import blake3

    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False


def sha256_hex(data: bytes) -> str:
    if HAS_BLAKE3:
        return blake3.blake3(data).hexdigest()
    return hashlib.sha256(data).hexdigest()


def hash_leaf(key: str, value: Any) -> str:
    """Computes cryptographic hash of a single key-value state leaf."""
    raw = f"{key}:{json.dumps(value, sort_keys=True, default=str)}".encode("utf-8")
    return sha256_hex(raw)


def hash_nodes(left_hash: str, right_hash: str) -> str:
    """Computes cryptographic hash of an internal Merkle node from child hashes."""
    combined = (left_hash + right_hash).encode("utf-8")
    return sha256_hex(combined)


class MerkleNode:
    def __init__(
        self,
        key: Optional[str] = None,
        value: Any = None,
        left: Optional["MerkleNode"] = None,
        right: Optional["MerkleNode"] = None,
        hash_val: Optional[str] = None,
    ):
        self.key = key
        self.value = value
        self.left = left
        self.right = right
        if hash_val is not None:
            self.hash = hash_val
        elif key is not None and value is not None:
            self.hash = hash_leaf(key, value)
        elif left is not None and right is not None:
            self.hash = hash_nodes(left.hash, right.hash)
        else:
            self.hash = sha256_hex(b"")


class MerkleDAG:
    def __init__(self, items: Optional[Dict[str, Any]] = None):
        self.root: Optional[MerkleNode] = None
        if items:
            self.build(items)

    def build(self, items: Dict[str, Any]) -> None:
        sorted_items = sorted(items.items())
        self.root = self._build_tree(sorted_items)

    def _build_tree(self, items: List[Tuple[str, Any]]) -> Optional[MerkleNode]:
        if not items:
            return MerkleNode(hash_val=sha256_hex(b"empty"))

        nodes = [MerkleNode(key=k, value=v) for k, v in items]

        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    parent = MerkleNode(left=nodes[i], right=nodes[i + 1])
                else:
                    parent = nodes[i]
                next_level.append(parent)
            nodes = next_level
        return nodes[0]

    def get_root_hash(self) -> str:
        if self.root is None:
            return sha256_hex(b"empty")
        return self.root.hash

    def compare(self, remote_root: Optional[MerkleNode]) -> List[str]:
        divergent_keys: List[str] = []
        self._compare_nodes(self.root, remote_root, divergent_keys)
        return sorted(list(set(divergent_keys)))

    def _compare_nodes(
        self,
        local_node: Optional[MerkleNode],
        remote_node: Optional[MerkleNode],
        divergent_keys: List[str],
    ) -> None:
        if local_node is None and remote_node is None:
            return
        if local_node is not None and remote_node is not None and local_node.hash == remote_node.hash:
            return
        if local_node is not None and local_node.key is not None:
            divergent_keys.append(local_node.key)
        if remote_node is not None and remote_node.key is not None:
            divergent_keys.append(remote_node.key)
        if local_node is not None:
            self._compare_nodes(local_node.left, remote_node.left if remote_node else None, divergent_keys)
            self._compare_nodes(local_node.right, remote_node.right if remote_node else None, divergent_keys)
