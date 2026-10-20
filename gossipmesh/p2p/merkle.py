import hashlib
from typing import Dict, List, Optional, Tuple


class MerkleNode:
    def __init__(
        self, key: str, value_hash: str, left: Optional["MerkleNode"] = None, right: Optional["MerkleNode"] = None
    ):
        self.key = key
        self.value_hash = value_hash
        self.left = left
        self.right = right
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        hasher = hashlib.sha256()
        hasher.update(self.key.encode("utf-8"))
        hasher.update(self.value_hash.encode("utf-8"))
        if self.left:
            hasher.update(self.left.hash.encode("utf-8"))
        if self.right:
            hasher.update(self.right.hash.encode("utf-8"))
        return hasher.hexdigest()


class MerkleTree:
    def __init__(self, data: Dict[str, str]):
        sorted_items = sorted(data.items(), key=lambda x: x[0])
        self.root = self._build_tree(sorted_items)

    def _build_tree(self, items: List[Tuple[str, str]]) -> Optional[MerkleNode]:
        if not items:
            return None
        if len(items) == 1:
            k, v = items[0]
            v_hash = hashlib.sha256(v.encode("utf-8")).hexdigest()
            return MerkleNode(key=k, value_hash=v_hash)

        mid = len(items) // 2
        left_node = self._build_tree(items[:mid])
        right_node = self._build_tree(items[mid:])

        combined_key = f"{items[0][0]}-{items[-1][0]}"
        v_hash = hashlib.sha256(combined_key.encode("utf-8")).hexdigest()
        return MerkleNode(key=combined_key, value_hash=v_hash, left=left_node, right=right_node)

    def get_root_hash(self) -> Optional[str]:
        return self.root.hash if self.root else None

    def get_diff(
        self, other_root: Optional["MerkleNode"], current_node: Optional[MerkleNode], divergent_keys: List[str]
    ) -> List[str]:
        if current_node is None:
            return divergent_keys
        if other_root is None:
            self._collect_keys(current_node, divergent_keys)
            return divergent_keys
        if current_node.hash == other_root.hash:
            return divergent_keys

        if not current_node.left and not current_node.right and not other_root.left and not other_root.right:
            if current_node.key == other_root.key and current_node.value_hash != other_root.value_hash:
                if current_node.key not in divergent_keys:
                    divergent_keys.append(current_node.key)
            return divergent_keys

        self.get_diff(other_root.left, current_node.left, divergent_keys)
        self.get_diff(other_root.right, current_node.right, divergent_keys)

        if not current_node.left and not current_node.right:
            if current_node.key not in divergent_keys:
                divergent_keys.append(current_node.key)

        return divergent_keys

    def _collect_keys(self, node: Optional[MerkleNode], keys: List[str]):
        if not node:
            return
        if not node.left and not node.right:
            if node.key not in keys:
                keys.append(node.key)
        else:
            self._collect_keys(node.left, keys)
            self._collect_keys(node.right, keys)
