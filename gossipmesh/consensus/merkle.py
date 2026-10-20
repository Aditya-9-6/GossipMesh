import hashlib
from typing import Dict, List, Optional, Tuple


def hash_data(data: str) -> str:
    """Computes SHA-256 hash for a given string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_pair(left: str, right: str) -> str:
    """Computes parent hash from left and right child hashes."""
    combined = left + right
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class MerkleNode:
    """Represents a node in the Merkle tree."""

    def __init__(self, key: Optional[str] = None, value_hash: Optional[str] = None):
        self.key = key
        self.value_hash = value_hash
        self.left: Optional[MerkleNode] = None
        self.right: Optional[MerkleNode] = None
        self.hash = value_hash if value_hash else ""


class MerkleTree:
    """Hierarchical Merkle tree for state partitions and anti-entropy sync."""

    def __init__(self, items: Optional[Dict[str, str]] = None):
        self.root: Optional[MerkleNode] = None
        self.items: Dict[str, str] = {}
        if items:
            for k, v in items.items():
                self.insert(k, v)

    def insert(self, key: str, value: str) -> None:
        """Inserts or updates a key-value pair and recomputes the tree."""
        self.items[key] = value
        self._rebuild()

    def _rebuild(self) -> None:
        """Rebuilds the Merkle tree from sorted items."""
        sorted_keys = sorted(self.items.keys())
        if not sorted_keys:
            self.root = None
            return
        nodes = [MerkleNode(key=k, value_hash=hash_data(self.items[k])) for k in sorted_keys]
        self.root = self._build_level(nodes)

    def _build_level(self, nodes: List[MerkleNode]) -> MerkleNode:
        """Recursively builds tree levels from node lists (<60 LOC)."""
        if len(nodes) == 1:
            return nodes[0]
        next_level = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            parent = MerkleNode()
            parent.left = left
            parent.right = right
            parent.hash = hash_pair(left.hash, right.hash)
            next_level.append(parent)
        return self._build_level(next_level)

    def get_root_hash(self) -> str:
        """Returns root fingerprint of the Merkle tree."""
        return self.root.hash if self.root else hash_data("")

    def get_subtree_fingerprints(self) -> Dict[str, str]:
        """Returns all subtree keys and their respective fingerprints."""
        fingerprints = {}
        if not self.root:
            return fingerprints
        queue = [(self.root, "root")]
        while queue:
            node, path = queue.pop(0)
            if node.key:
                fingerprints[node.key] = node.hash
            if node.left:
                queue.append((node.left, path + ".left"))
            if node.right and node.right != node.left:
                queue.append((node.right, path + ".right"))
        return fingerprints
