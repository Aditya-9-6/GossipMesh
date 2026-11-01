import blake3
import json
from typing import Dict, List, Optional, Tuple, Any


def blake3_hex(data: bytes) -> str:
    """Computes blake3 hex digest for given bytes."""
    hasher = blake3.blake3()
    hasher.update(data)
    return hasher.hexdigest()


def hash_leaf(key: str, value: Any) -> str:
    """Computes cryptographic hash of a single key-value state leaf using blake3."""
    raw = f"{key}:{json.dumps(value, sort_keys=True, default=str)}".encode("utf-8")
    return blake3_hex(raw)


def hash_nodes(left_hash: str, right_hash: str) -> str:
    """Computes cryptographic hash of an internal Merkle node from child hashes using blake3."""
    combined = (left_hash + right_hash).encode("utf-8")
    return blake3_hex(combined)


class MerkleNode:
    """Represents a node within the Hierarchical Merkle-DAG state tree."""

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
            self._hash = blake3_hex(b"")

    @property
    def hash(self) -> str:
        return self._hash

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class MerkleDAG:
    """Blake3 Merkle-DAG supporting incremental state reconciliation and O(log N) diff traversal."""

    def __init__(self, state_map: Optional[Dict[str, Any]] = None):
        self.state_map: Dict[str, Any] = dict(state_map) if state_map is not None else {}
        self.root: MerkleNode = self._build_tree(sorted(self.state_map.items()))

    def _build_tree(self, items: List[Tuple[str, Any]]) -> MerkleNode:
        if not items:
            return MerkleNode(hash_val=blake3_hex(b"empty"))

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
        Recursively traverses local and remote Merkle DAGs in O(log N)
        to isolate and return keys that have diverged.
        """
        divergent_keys: List[str] = []
        self._compare_nodes(self.root, remote_root, divergent_keys)
        return sorted(list(set(divergent_keys)))

    def _compare_nodes(
        self, local: Optional[MerkleNode], remote: Optional[MerkleNode], divergent_keys: List[str]
    ) -> None:
        if local is None or remote is None:
            return
        if local.hash == remote.hash:
            return

        if local.is_leaf and remote.is_leaf:
            if local.key is not None:
                divergent_keys.append(local.key)
            return

        self._compare_nodes(local.left, remote.left, divergent_keys)
        self._compare_nodes(local.right, remote.right, divergent_keys)
