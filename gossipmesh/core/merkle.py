import hashlib
import json
from typing import Dict, List, Optional, Any


class MerkleNode:
    """Represents a node in the SHA-256 Merkle-DAG state tree."""

    def __init__(
        self,
        key: Optional[str] = None,
        value: Optional[Any] = None,
        left: Optional["MerkleNode"] = None,
        right: Optional["MerkleNode"] = None,
    ):
        self.key = key
        self.value = value
        self.left = left
        self.right = right
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        hasher = hashlib.sha256()
        if self.key is not None:
            hasher.update(self.key.encode("utf-8"))
        if self.value is not None:
            val_str = json.dumps(self.value, sort_keys=True, default=str)
            hasher.update(val_str.encode("utf-8"))
        if self.left is not None:
            hasher.update(self.left.hash.encode("utf-8"))
        if self.right is not None:
            hasher.update(self.right.hash.encode("utf-8"))
        return hasher.hexdigest()


class MerkleDAG:
    """SHA-256 Merkle-DAG State Reconciler for distributed agent states."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self.data: Dict[str, Any] = data or {}
        self.root: Optional[MerkleNode] = None
        self.build_tree()

    def build_tree(self) -> None:
        sorted_keys = sorted(self.data.keys())
        leaves = [MerkleNode(key=k, value=self.data[k]) for k in sorted_keys]
        self.root = self._build_recursive(leaves)

    def _build_recursive(self, nodes: List[MerkleNode]) -> Optional[MerkleNode]:
        if not nodes:
            return None
        if len(nodes) == 1:
            return nodes[0]

        next_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else None
            parent = MerkleNode(left=left, right=right)
            next_level.append(parent)
        return self._build_recursive(next_level)

    def get_root_hash(self) -> Optional[str]:
        return self.root.hash if self.root else None

    def get_state(self) -> Dict[str, Any]:
        return self.data

    def update_state(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.build_tree()

    def remove_state(self, key: str) -> None:
        if key in self.data:
            del self.data[key]
            self.build_tree()

    def find_divergences(
        self, peer_root: Optional[str], peer_node: Optional[MerkleNode] = None, local_node: Optional[MerkleNode] = None
    ) -> List[str]:
        """Pinpoints divergent state branches in O(log N) traversal time."""
        if peer_node is None:
            peer_node = peer_root

        local_node = local_node or self.root

        if not local_node and not peer_node:
            return []
        if local_node and peer_node and isinstance(peer_node, str):
            if local_node.hash == peer_node:
                return []
            return list(self.data.keys())

        if local_node and peer_node and isinstance(peer_node, MerkleNode):
            if local_node.hash == peer_node.hash:
                return []

            if local_node.key is not None and local_node.key == peer_node.key:
                if local_node.hash != peer_node.hash:
                    return [local_node.key]
                return []

            divergent_keys = []
            left_local = getattr(local_node, "left", None)
            left_peer = getattr(peer_node, "left", None)
            right_local = getattr(local_node, "right", None)
            right_peer = getattr(peer_node, "right", None)

            if (
                (left_local and left_peer and getattr(left_local, "hash", None) != getattr(left_peer, "hash", None))
                or (left_local and not left_peer)
                or (not left_local and left_peer)
            ):
                divergent_keys.extend(self.find_divergences(None, left_peer, left_local))

            if (
                (right_local and right_peer and getattr(right_local, "hash", None) != getattr(right_peer, "hash", None))
                or (right_local and not right_peer)
                or (not right_local and right_peer)
            ):
                divergent_keys.extend(self.find_divergences(None, right_peer, right_local))

            return list(set(divergent_keys))

        return list(self.data.keys())
