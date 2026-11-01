"""Cryptographic Merkle-DAG State Reconciler for GossipMesh.

Provides a bounded, O(log N) tree traversal algorithm to pinpoint divergent agent
state branches over the gossip transport layer using SHA-256 hashes.
"""

import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any


def sha256_hex(data: bytes) -> str:
    """Computes SHA-256 hex digest for given bytes."""
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
    """Represents a node within the Merkle-DAG state tree."""

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
            self._hash = hash_val
        elif key is not None and left is None and right is None:
            self._hash = hash_leaf(key, value)
        elif left is not None and right is not None:
            self._hash = hash_nodes(left.hash, right.hash)
        elif left is not None:
            self._hash = left.hash
        else:
            self._hash = sha256_hex(b"")

    @property
    def hash(self) -> str:
        return self._hash

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class MerkleDAG:
    """SHA-256 Merkle-DAG supporting incremental state reconciliation and O(log N) diff traversal."""

    def __init__(self, state_map: Optional[Dict[str, Any]] = None):
        self.state_map: Dict[str, Any] = dict(state_map) if state_map is not None else {}
        self.root: MerkleNode = self._build_tree(sorted(self.state_map.items()))

    def _build_tree(self, items: List[Tuple[str, Any]]) -> MerkleNode:
        if not items:
            return MerkleNode(hash_val=sha256_hex(b"empty"))

        nodes = [MerkleNode(key=k, value=v) for k, v in items]

        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                parent = MerkleNode(left=left, right=right)
                next_level.append(parent)
            nodes = next_level

        return nodes[0]

    @property
    def root_hash(self) -> str:
        return self.root.hash

    def find_divergences(self, remote_root: MerkleNode) -> List[str]:
        """
        Recursively traverses local and remote Merkle trees in O(log N)
        to isolate and return keys that have diverged.
        """
        divergent_keys: List[str] = []
        self._compare_nodes(self.root, remote_root, divergent_keys)
        return sorted(list(set(divergent_keys)))

    def _compare_nodes(
        self, local_node: Optional[MerkleNode], remote_node: Optional[MerkleNode], divergent_keys: List[str]
    ) -> None:
        if local_node is None and remote_node is None:
            return
        if local_node is not None and remote_node is not None and local_node.hash == remote_node.hash:
            return

        if local_node is not None and local_node.is_leaf:
            if local_node.key is not None:
                divergent_keys.append(local_node.key)
            return

        if remote_node is not None and remote_node.is_leaf:
            if remote_node.key is not None:
                divergent_keys.append(remote_node.key)
            return

        local_left = local_node.left if local_node else None
        local_right = local_node.right if local_node else None
        remote_left = remote_node.left if remote_node else None
        remote_right = remote_node.right if remote_node else None

        self._compare_nodes(local_left, remote_left, divergent_keys)
        self._compare_nodes(local_right, remote_right, divergent_keys)

    def get_proof(self, key: str) -> List[Dict[str, str]]:
        """Generates a cryptographic inclusion proof path for a specific state key."""
        proof = []
        self._collect_proof(self.root, key, proof)
        return proof

    def _collect_proof(self, node: Optional[MerkleNode], key: str, proof: List[Dict[str, str]]) -> bool:
        if node is None:
            return False
        if node.is_leaf:
            return node.key == key

        if node.left and self._collect_proof(node.left, key, proof):
            if node.right:
                proof.append({"sibling_hash": node.right.hash, "position": "right"})
            return True

        if node.right and self._collect_proof(node.right, key, proof):
            if node.left:
                proof.append({"sibling_hash": node.left.hash, "position": "left"})
            return True

        return False
