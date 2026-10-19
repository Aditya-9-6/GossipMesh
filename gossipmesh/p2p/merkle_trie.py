import hashlib
import json
from typing import Dict, Any, Optional, List


class MerkleNode:
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
        if self.left or self.right:
            left_hash = self.left.hash if self.left else ""
            right_hash = self.right.hash if self.right else ""
            hasher.update(f"{left_hash}:{right_hash}".encode("utf-8"))
        else:
            val_str = json.dumps(self.value, sort_keys=True) if self.value is not None else ""
            hasher.update(f"{self.key}:{val_str}".encode("utf-8"))
        return hasher.hexdigest()


class MerklePatriciaTree:
    def __init__(self):
        self.store: Dict[str, Any] = {}
        self.root: Optional[MerkleNode] = None

    def insert(self, key: str, value: Any) -> None:
        self.store[key] = value
        self._rebuild_tree()

    def delete(self, key: str) -> bool:
        if key in self.store:
            del self.store[key]
            self._rebuild_tree()
            return True
        return False

    def _rebuild_tree(self) -> None:
        if not self.store:
            self.root = None
            return
        sorted_keys = sorted(self.store.keys())
        nodes = [MerkleNode(key=k, value=self.store[k]) for k in sorted_keys]
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else None
                parent = MerkleNode(left=left, right=right)
                next_level.append(parent)
            nodes = next_level
        self.root = nodes[0]

    def get_root_hash(self) -> str:
        if not self.root:
            return hashlib.sha256(b"empty").hexdigest()
        return self.root.hash

    def get_proof(self, key: str) -> List[str]:
        if key not in self.store:
            return []
        proof = []
        curr = self.root
        while curr and not (curr.key == key and curr.value == self.store.get(key)):
            if curr.left and key <= (curr.left.key if curr.left.key else "zzzz"):
                if curr.right:
                    proof.append(f"R:{curr.right.hash}")
                curr = curr.left
            elif curr.right:
                if curr.left:
                    proof.append(f"L:{curr.left.hash}")
                curr = curr.right
            else:
                break
        return proof
