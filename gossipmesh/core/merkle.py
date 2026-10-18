import hashlib
from typing import Dict, List, Optional, Any, Tuple

class MerkleNode:
    def __init__(self, key: str, value_hash: str, left: Optional['MerkleNode'] = None, right: Optional['MerkleNode'] = None):
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
        return hasher.hexdigest()


class MerkleDAG:
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self.root: Optional[MerkleNode] = None
        self._data: Dict[str, str] = {}
        if data:
            for k, v in data.items():
                self.insert(k, v)

    @staticmethod
    def _hash_value(value: Any) -> str:
        hasher = hashlib.sha256()
        if isinstance(value, str):
            hasher.update(value.encode('utf-8'))
        elif isinstance(value, bytes):
            hasher.update(value)
        else:
            hasher.update(str(value).encode('utf-8'))
        return hasher.hexdigest()

    def insert(self, key: str, value: Any) -> None:
        val_hash = self._hash_value(value)
        self._data[key] = val_hash
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        sorted_keys = sorted(self._data.keys())
        if not sorted_keys:
            self.root = None
            return
        nodes = [MerkleNode(k, self._data[k]) for k in sorted_keys]
        self.root = self._build_sub_tree(nodes)

    def _build_sub_tree(self, nodes: List[MerkleNode]) -> MerkleNode:
        if not nodes:
            raise ValueError("Cannot build subtree from empty nodes list")
        if len(nodes) == 1:
            return nodes[0]
        mid = len(nodes) // 2
        left_node = self._build_sub_tree(nodes[:mid])
        right_node = self._build_sub_tree(nodes[mid:])
        
        combined_key = f"{left_node.key}:{right_node.key}"
        combined_hash_input = left_node.hash + right_node.hash
        parent_val_hash = hashlib.sha256(combined_hash_input.encode('utf-8')).hexdigest()
        
        return MerkleNode(combined_key, parent_val_hash, left=left_node, right=right_node)

    @property
    def root_hash(self) -> Optional[str]:
        return self.root.hash if self.root else None

    def get_divergent_keys(self, other_root: Optional[str]) -> List[str]:
        if self.root_hash == other_root:
            return []
        return sorted(list(self._data.keys()))

    def generate_proof(self, key: str) -> List[Dict[str, Any]]:
        if not self.root or key not in self._data:
            return []
        proof = []
        curr = self.root
        while curr and (curr.left or curr.right):
            if curr.left and curr.right:
                if key <= curr.left.key:
                    proof.append({"direction": "right", "hash": curr.right.hash})
                    curr = curr.left
                else:
                    proof.append({"direction": "left", "hash": curr.left.hash})
                    curr = curr.right
            elif curr.left:
                curr = curr.left
            elif curr.right:
                curr = curr.right
            else:
                break
        return proof

    def reconcile(self, remote_root: Optional[str], remote_keys: Any) -> List[str]:
        if self.root_hash == remote_root:
            return []
        
        # Support both List[str] (keys) and Dict[str, str] (key -> value_hash) for reconciliation
        if isinstance(remote_keys, dict):
            remote_dict = remote_keys
        else:
            remote_dict = {k: "" for k in remote_keys}
            
        local_keys = set(self._data.keys())
        remote_set = set(remote_dict.keys())
        
        divergent = set(local_keys.symmetric_difference(remote_set))
        for k in local_keys.intersection(remote_set):
            if k in remote_dict and remote_dict[k] and self._data[k] != remote_dict[k]:
                divergent.add(k)
                
        return sorted(list(divergent))
