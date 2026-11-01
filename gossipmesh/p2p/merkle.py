import json
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    import blake3

    def _blake3_hash(data: bytes) -> str:
        return blake3.blake3(data).hexdigest()
except ImportError:

    def _blake3_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


def blake3_hex(data: bytes) -> str:
    return _blake3_hash(data)


def hash_leaf(key: str, value: Any) -> str:
    raw = f"{key}:{json.dumps(value, sort_keys=True, default=str)}".encode("utf-8")
    return blake3_hex(raw)


def hash_nodes(left_hash: str, right_hash: str) -> str:
    combined = (left_hash + right_hash).encode("utf-8")
    return blake3_hex(combined)


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
        if hash_val:
            self.hash = hash_val
        elif key is not None:
            self.hash = hash_leaf(key, value)
        elif left and right:
            self.hash = hash_nodes(left.hash, right.hash)
        else:
            self.hash = blake3_hex(b"empty")


class MerkleDAG:
    def __init__(self, items: Optional[List[Tuple[str, Any]]] = None):
        self.items = sorted(items or [], key=lambda x: x[0])
        self.root = self._build_tree(self.items)

    def _build_tree(self, items: List[Tuple[str, Any]]) -> MerkleNode:
        if not items:
            return MerkleNode(hash_val=blake3_hex(b"empty"))

        nodes = [MerkleNode(key=k, value=v) for k, v in items]
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    parent = MerkleNode(left=nodes[i], right=nodes[i + 1])
                    next_level.append(parent)
                else:
                    next_level.append(nodes[i])
            nodes = next_level
        return nodes[0]

    def get_root_hash(self) -> str:
        return self.root.hash

    def find_divergence(self, remote_root: Optional[MerkleNode]) -> List[str]:
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
        if (
            local_node is not None
            and local_node.key is not None
            and (remote_node is None or remote_node.key == local_node.key)
        ):
            if remote_node is None or local_node.value != remote_node.value:
                divergent_keys.append(local_node.key)
            return
        if local_node is None or remote_node is None:
            if local_node and local_node.key:
                divergent_keys.append(local_node.key)
            if remote_node and remote_node.key:
                divergent_keys.append(remote_node.key)
            return

        self._compare_nodes(local_node.left, remote_node.left, divergent_keys)
        self._compare_nodes(local_node.right, remote_node.right, divergent_keys)
