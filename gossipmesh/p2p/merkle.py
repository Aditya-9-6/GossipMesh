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
        hasher.update(self.key.encode('utf-8'))
        hasher.update(self.value_hash.encode('utf-8'))
        if self.left:
            hasher.update(self.left.hash.encode('utf-8'))
        if self.right:
            hasher.update(self.right.hash.encode('utf-8'))
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
        sorted_items = sorted(data.items(), key=lambda x: x[0])
        self.root = self._build_tree(sorted_items)

    def _build_tree(self, items: List[Tuple[str, str]]) -> Optional[MerkleNode]:
        if not items:
            return None
        if len(items) == 1:
            k, v = items[0]
            v_hash = hashlib.sha256(v.encode('utf-8')).hexdigest()
            return MerkleNode(key=k, value_hash=v_hash)
        
        mid = len(items) // 2
        left_node = self._build_tree(items[:mid])
        right_node = self._build_tree(items[mid:])
        
        combined_key = f"{items[0][0]}-{items[-1][0]}"
        v_hash = hashlib.sha256(combined_key.encode('utf-8')).hexdigest()
        return MerkleNode(key=combined_key, value_hash=v_hash, left=left_node, right=right_node)

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
            
        if not self_node:
            return sorted(list(diffs))

        if not other_root:
            self._collect_keys(self_node, diffs)
            return sorted(list(diffs))

        if self_node.key:
            other_val_hash = other_root.value_hash if other_root else None
            if other_root is None or self_node.value_hash != other_val_hash:
                if not self_node.left and not self_node.right and (not other_root or (not other_root.left and not other_root.right)):
                    diffs.add(self_node.key)
                elif not other_root:
                    self._collect_keys(self_node, diffs)

        self.find_divergent_keys(other_root.left if other_root else None, self_node.left, diffs)
        self.find_divergent_keys(other_root.right if other_root else None, self_node.right, diffs)
        return sorted(list(diffs))

    def _collect_keys(self, node: Optional[MerkleNode], keys: Set[str]):
        if not node:
            return
        keys.add(node.key)
        self._collect_keys(node.left, keys)
        self._collect_keys(node.right, keys)

    def get_diff(self, other_root: Optional['MerkleNode'], current_node: Optional[MerkleNode], divergent_keys: List[str]) -> List[str]:
        if current_node is None:
            return divergent_keys
        if other_root is None:
            self._collect_keys_list(current_node, divergent_keys)
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

    def _collect_keys_list(self, node: Optional[MerkleNode], keys: List[str]):
        if not node:
            return
        if not node.left and not node.right:
            if node.key not in keys:
                keys.append(node.key)
        else:
            self._collect_keys_list(node.left, keys)
            self._collect_keys_list(node.right, keys)
