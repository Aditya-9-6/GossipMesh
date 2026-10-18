import hashlib
import json
from typing import Dict, List, Tuple, Any

class MerkleIntervalNode:
    def __init__(self, start_key: str, end_key: str, digest: str):
        self.start_key = start_key
        self.end_key = end_key
        self.digest = digest

class VectorClockEntropyEngine:
    @staticmethod
    def data_hasher(d: Any) -> str:
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode("utf-8")).hexdigest()

    @classmethod
    def compute_digest(cls, items: Dict[str, Any]) -> str:
        if not items:
            return hashlib.sha256(b"").hexdigest()
        return cls.data_hasher(items)

    @classmethod
    def build_merkle_tree(cls, state_store: Dict[str, Any], bucket_size: int = 16) -> List[MerkleIntervalNode]:
        sorted_keys = sorted(state_store.keys())
        if not sorted_keys:
            return [MerkleIntervalNode("", "", cls.compute_digest({}))]
        nodes = []
        for i in range(0, len(sorted_keys), bucket_size):
            bucket_keys = sorted_keys[i:i + bucket_size]
            bucket_data = {k: state_store[k] for k in bucket_keys}
            digest = cls.compute_digest(bucket_data)
            nodes.append(MerkleIntervalNode(bucket_keys[0], bucket_keys[-1], digest))
        return nodes

    @staticmethod
    def compare_clocks(clock_a: Dict[str, int], clock_b: Dict[str, int]) -> str:
        keys = set(clock_a.keys()).union(set(clock_b.keys()))
        greater = False
        lesser = False
        for k in keys:
            va = clock_a.get(k, 0)
            vb = clock_b.get(k, 0)
            if va > vb:
                greater = True
            elif va < vb:
                lesser = True
        if greater and not lesser:
            return "after"
        if lesser and not greater:
            return "before"
        if not greater and not lesser:
            return "equal"
        return "concurrent"

    @classmethod
    def reconcile_state(cls, local_state: Dict[str, Any], local_clock: Dict[str, int], peer_state: Dict[str, Any], peer_clock: Dict[str, int]) -> Tuple[Dict[str, Any], Dict[str, int]]:
        relation = cls.compare_clocks(local_clock, peer_clock)
        if relation == "after":
            return local_state, local_clock
        if relation == "before":
            return peer_state, peer_clock
        merged_state = {**peer_state, **local_state}
        merged_clock = {k: max(local_clock.get(k, 0), peer_clock.get(k, 0)) for k in set(local_clock).union(peer_clock)}
        return merged_state, merged_clock
