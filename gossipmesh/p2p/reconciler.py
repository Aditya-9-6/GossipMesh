import hashlib
import json
from typing import Dict, List, Tuple, Any, Optional
from gossipmesh.p2p.vector_clock import VectorClock


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
        self.root = self._build_tree(sorted(data.items()))

    def _build_tree(self, items: List[Tuple[str, str]]) -> Optional[MerkleNode]:
        if not items:
            return None
        if len(items) == 1:
            k, v = items[0]
            val_hash = hashlib.sha256(v.encode("utf-8")).hexdigest()
            return MerkleNode(k, val_hash)

        mid = len(items) // 2
        left_node = self._build_tree(items[:mid])
        right_node = self._build_tree(items[mid:])

        k, v = items[mid]
        val_hash = hashlib.sha256(v.encode("utf-8")).hexdigest()
        return MerkleNode(k, val_hash, left=left_node, right=right_node)

    def get_root_hash(self) -> Optional[str]:
        return self.root.hash if self.root else None


class AntiEntropyReconciler:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.store: Dict[str, str] = {}
        self.vector_clock = VectorClock()

    def set_state(self, key: str, value: str) -> None:
        self.store[key] = value
        self.vector_clock.increment(self.node_id)

    def get_merkle_tree(self) -> MerkleTree:
        return MerkleTree(self.store)

    def find_differences(self, peer_store: Dict[str, str]) -> List[str]:
        diffs = []
        all_keys = set(self.store.keys()).union(set(peer_store.keys()))
        for k in all_keys:
            if self.store.get(k) != peer_store.get(k):
                diffs.append(k)
        return diffs

    def reconcile(self, peer_id: str, peer_vc_dict: Dict[str, int], peer_root_hash: Optional[str]) -> str:
        peer_vc = VectorClock.from_dict(peer_vc_dict)
        comparison = self.vector_clock.compare(peer_vc)

        local_tree = self.get_merkle_tree()
        if local_tree.get_root_hash() == peer_root_hash:
            return "NO_SYNC_NEEDED"

        if comparison == "BEFORE":
            return "PULL_FROM_PEER"
        elif comparison == "AFTER":
            return "PUSH_TO_PEER"
        else:
            return "EXCHANGE_MERKLE"
