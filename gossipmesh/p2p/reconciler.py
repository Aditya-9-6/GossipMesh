import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from gossipmesh.p2p.vector_clock import VectorClock


class MerkleNode:
    """Node in a Merkle tree representing a hash and optional children."""

    def __init__(
        self,
        hash_val: str,
        left: Optional["MerkleNode"] = None,
        right: Optional["MerkleNode"] = None,
        key: Optional[str] = None,
        value_hash: Optional[str] = None,
    ) -> None:
        self.hash_val = hash_val
        self.left = left
        self.right = right
        self.key = key
        self.value_hash = value_hash
        if value_hash and not hash_val:
            self.hash_val = self._compute_hash()

    def _compute_hash(self) -> str:
        hasher = hashlib.sha256()
        if self.key:
            hasher.update(self.key.encode("utf-8"))
        if self.value_hash:
            hasher.update(self.value_hash.encode("utf-8"))
        if self.left:
            hasher.update(self.left.hash_val.encode("utf-8"))
        if self.right:
            hasher.update(self.right.hash_val.encode("utf-8"))
        return hasher.hexdigest()


class MerkleTree:
    """Merkle Tree for detecting state divergence between peers."""

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        self.data: Dict[str, Any] = dict(data) if data is not None else {}
        self.root: Optional[MerkleNode] = None
        self.leaf_hashes: Dict[str, str] = {}
        self.root_hash: str = ""
        self._build_tree()

    @staticmethod
    def _sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _leaf_hash(self, key: str, value: Any) -> str:
        try:
            val_repr = json.dumps(value, sort_keys=True, default=str)
        except Exception:
            val_repr = str(value)
        return self._sha256(f"{key}:{val_repr}")

    def _build_tree(self) -> None:
        if not self.data:
            self.root_hash = self._sha256("")
            return

        sorted_keys = sorted(self.data.keys())
        leaves: List[MerkleNode] = []
        for k in sorted_keys:
            h = self._leaf_hash(k, self.data[k])
            self.leaf_hashes[k] = h
            leaves.append(MerkleNode(hash_val=h, key=k))

        current_level = leaves
        while len(current_level) > 1:
            next_level: List[MerkleNode] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                    combined_hash = self._sha256(left.hash_val + right.hash_val)
                    next_level.append(
                        MerkleNode(hash_val=combined_hash, left=left, right=right)
                    )
                else:
                    next_level.append(left)
            current_level = next_level

        self.root = current_level[0]
        self.root_hash = self.root.hash_val

    def get_root_hash(self) -> Optional[str]:
        return self.root_hash if self.root else None

    def get_diff(self, other: "MerkleTree") -> List[str]:
        """Returns keys that differ between this tree and another."""
        if self.root_hash == other.root_hash:
            return []

        all_keys = set(self.data.keys()).union(set(other.data.keys()))
        diff_keys: List[str] = []
        for k in sorted(all_keys):
            if k not in self.data or k not in other.data:
                diff_keys.append(k)
            elif self.leaf_hashes.get(k) != other.leaf_hashes.get(k):
                diff_keys.append(k)

        return diff_keys


class VectorClockReconciler:
    """Reconciles peer states using vector clocks and Merkle diff digests."""

    def __init__(
        self,
        node_id: str,
        local_state: Dict[str, Any],
        vector_clock: VectorClock,
    ) -> None:
        self.node_id = node_id
        self.local_state = local_state
        self.vector_clock = vector_clock

    def generate_digest(self) -> Tuple[VectorClock, str]:
        """Generates the local vector clock digest and Merkle root hash."""
        tree = MerkleTree(self.local_state)
        return self.vector_clock.clone(), tree.root_hash

    def reconcile(
        self,
        remote_vc: VectorClock,
        remote_root_digest: Any,
        remote_state: Dict[str, Any],
    ) -> List[str]:
        """Reconciles local state with remote state, returning differing keys."""
        local_tree = MerkleTree(self.local_state)
        remote_tree = MerkleTree(remote_state)

        if (
            isinstance(remote_root_digest, str)
            and local_tree.root_hash == remote_root_digest
            and not remote_state
        ):
            return []

        return local_tree.get_diff(remote_tree)


class AntiEntropyReconciler:
    """Anti-entropy reconciler using vector clocks and Merkle trees."""

    def __init__(self, node_id: str) -> None:
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
