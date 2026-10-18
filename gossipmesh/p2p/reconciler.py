import hashlib
from typing import Dict, List, Tuple, Any, Optional
from gossipmesh.p2p.vector_clock import VectorClock

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

class MerkleTree:
    def __init__(self, entries: Optional[Dict[str, str]] = None):
        self.root: Optional[MerkleNode] = None
        if entries:
            self.build_tree(entries)

    def build_tree(self, entries: Dict[str, str]):
        nodes = []
        for key, val in sorted(entries.items()):
            v_hash = hashlib.sha256(val.encode('utf-8')).hexdigest()
            nodes.append(MerkleNode(key, v_hash))
        
        if not nodes:
            self.root = None
            return

        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i+1] if i + 1 < len(nodes) else None
                parent = MerkleNode(left.key, left.value_hash, left, right)
                next_level.append(parent)
            nodes = next_level
        self.root = nodes[0]

    def get_root_hash(self) -> str:
        return self.root.hash if self.root else hashlib.sha256(b"").hexdigest()

class AntiEntropyReconciler:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.store: Dict[str, str] = {}
        self.vector_clock = VectorClock({node_id: 0})

    def set_state(self, key: str, value: str):
        self.store[key] = value
        self.vector_clock.increment(self.node_id)

    def get_merkle_tree(self) -> MerkleTree:
        return MerkleTree(self.store)

    def reconcile(self, peer_id: str, peer_vc_dict: Dict[str, int], peer_root_hash: str) -> str:
        peer_vc = VectorClock.from_dict(peer_vc_dict)
        comparison = self.vector_clock.compare(peer_vc)
        
        if comparison == "EQUAL":
            if self.get_merkle_tree().get_root_hash() == peer_root_hash:
                return "NO_SYNC_NEEDED"
            return "MERKLE_SYNC"
        elif comparison == "BEFORE":
            return "PULL_FROM_PEER"
        elif comparison == "AFTER":
            return "PUSH_TO_PEER"
        else:
            return "MERKLE_SYNC"
