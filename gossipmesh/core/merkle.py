import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash of given bytes."""
    return hashlib.sha256(data).hexdigest()


def hash_leaf(key: str, value: Any) -> str:
    """Compute cryptographic hash for a key-value leaf node."""
    serialized = json.dumps({"key": key, "value": value}, sort_keys=True).encode("utf-8")
    return compute_hash(serialized)


def hash_nodes(left_hash: str, right_hash: str) -> str:
    """Combine left and right child hashes to form a parent hash."""
    combined = (left_hash + right_hash).encode("utf-8")
    return compute_hash(combined)


class MerkleNode:
    """Represents a node in the Merkle-DAG."""

    def __init__(self, key: Optional[str] = None, value: Any = None, left: Optional['MerkleNode'] = None, right: Optional['MerkleNode'] = None):
        self.key = key
        self.value = value
        self.left = left
        self.right = right
        self.hash = self._compute_node_hash()

    def _compute_node_hash(self) -> str:
        if self.key is not None:
            return hash_leaf(self.key, self.value)
        
        left_h = self.left.hash if self.left else "0" * 64
        right_h = self.right.hash if self.right else "0" * 64
        return hash_nodes(left_h, right_h)


class MerkleDAG:
    """SHA-256 Merkle-DAG State Reconciler for GossipMesh peer states."""

    def __init__(self, state_dict: Optional[Dict[str, Any]] = None):
        self.state: Dict[str, Any] = state_dict or {}
        self.root: Optional[MerkleNode] = None
        self.rebuild()

    def rebuild(self) -> None:
        """Rebuild the Merkle-DAG from the current state dictionary."""
        sorted_items = sorted(self.state.items())
        leaves = [MerkleNode(key=k, value=v) for k, v in sorted_items]
        self.root = self._build_tree(leaves)

    def _build_tree(self, nodes: List[MerkleNode]) -> Optional[MerkleNode]:
        if not nodes:
            return None
        if len(nodes) == 1:
            return nodes[0]

        parent_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            parent = MerkleNode(left=left, right=right)
            parent_level.append(parent)

        return self._build_tree(parent_level)

    def get_root_hash(self) -> str:
        """Return the root hash of the Merkle-DAG."""
        if not self.root:
            return compute_hash(b"")
        return self.root.hash

    def update_state(self, key: str, value: Any) -> None:
        """Update or insert a key-value pair and rebuild the DAG."""
        self.state[key] = value
        self.rebuild()

    def get_divergent_keys(self, remote_root_hash: str, remote_leaves: Dict[str, str]) -> List[str]:
        """Pinpoint divergent keys by comparing local and remote leaf hashes in O(log N) fashion."""
        divergent = []
        for key, local_value in self.state.items():
            local_hash = hash_leaf(key, local_value)
            remote_hash = remote_leaves.get(key)
            if remote_hash != local_hash:
                divergent.append(key)

        for r_key in remote_leaves:
            if r_key not in self.state:
                divergent.append(r_key)

        return sorted(list(set(divergent)))

    def get_leaf_hashes(self) -> Dict[str, str]:
        """Return a dictionary mapping all keys to their respective leaf hashes."""
        return {k: hash_leaf(k, v) for k, v in self.state.items()}
