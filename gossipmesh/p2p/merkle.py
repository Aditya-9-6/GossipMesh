import hashlib
from typing import Dict, List, Optional, Tuple, Set


class MerkleNode:
    def __init__(
        self,
        key: str,
        value_hash: str,
        left: Optional['MerkleNode'] = None,
        right: Optional['MerkleNode'] = None,
    ):
        self.key = key
        self.value_hash = value_hash
        self.left = left
        self.right = right
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        hasher = hashlib.sha256()
        content = f"{self.key}:{self.value_hash}"
        if self.left:
            content += f":{self.left.hash}"
        if self.right:
            content += f":{self.right.hash}"
        hasher.update(content.encode('utf-8'))
        return hasher.hexdigest()


class MerkleTree:
    def __init__(self, data: Dict[str, str]):
        self.data = data
        items = sorted(data.items())
        self.root = self._build_tree(items)

    def _build_tree(self, items: List[Tuple[str, str]]) -> Optional[MerkleNode]:
        if not items:
            return None
        if len(items) == 1:
            k, v = items[0]
            vh = hashlib.sha256(v.encode('utf-8')).hexdigest()
            return MerkleNode(key=k, value_hash=vh)

        mid = len(items) // 2
        left_node = self._build_tree(items[:mid])
        right_node = self._build_tree(items[mid:])
        
        hasher = hashlib.sha256()
        l_hash = left_node.hash if left_node else ''
        r_hash = right_node.hash if right_node else ''
        hasher.update(f"{l_hash}:{r_hash}".encode('utf-8'))
        
        node = MerkleNode(key=items[mid][0], value_hash=hasher.hexdigest(), left=left_node, right=right_node)
        return node

    def get_root_hash(self) -> Optional[str]:
        return self.root.hash if self.root else None

    def find_divergent_keys(self, other_root: Optional['MerkleNode'], self_node: Optional[MerkleNode] = None, diffs: Optional[Set[str]] = None) -> List[str]:
        if diffs is None:
            diffs = set()
        if self_node is None:
            self_node = self.root
            
        if self_node is None and other_root is None:
            return sorted(list(diffs))
        if self_node and other_root and self_node.hash == other_root.hash:
            return sorted(list(diffs))
            
        if not self_node or not other_root:
            if self_node:
                self._collect_keys(self_node, diffs)
            return sorted(list(diffs))

        if self_node.key and (other_root is None or self_node.value_hash != other_root.value_hash):
            diffs.add(self_node.key)

        self.find_divergent_keys(other_root.left if other_root else None, self_node.left, diffs)
        self.find_divergent_keys(other_root.right if other_root else None, self_node.right, diffs)
        return sorted(list(diffs))

    def _collect_keys(self, node: Optional[MerkleNode], keys: Set[str]):
        if not node:
            return
        keys.add(node.key)
        self._collect_keys(node.left, keys)
        self._collect_keys(node.right, keys)
