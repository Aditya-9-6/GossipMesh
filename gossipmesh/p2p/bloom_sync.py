import math
import hashlib
import base64
import threading
from typing import Set, List, Dict, Any, Optional
from gossipmesh.p2p.digest import BloomFilterDigest


class HierarchicalBloomFilterDigest:
    """Hierarchical multi-tiered Bloom-filter digest synchronization tree for efficient P2P anti-entropy reconciliations."""

    def __init__(self, capacity: int = 10000, error_rate: float = 0.01, levels: int = 3) -> None:
        self.capacity = max(1, capacity)
        self.error_rate = min(max(0.0001, error_rate), 0.5)
        self.levels = max(1, min(levels, 8))
        self._lock = threading.Lock()

        # Construct generational tiers: level 0 is finest grain, higher levels aggregate broader scopes
        self.filters: List[BloomFilterDigest] = []
        curr_capacity = self.capacity
        for i in range(self.levels):
            # Each higher level scales capacity logarithmically or broadens acceptance
            lvl_capacity = max(100, curr_capacity // (2**i))
            self.filters.append(BloomFilterDigest(capacity=lvl_capacity, error_rate=self.error_rate))

    @property
    def tier_count(self) -> int:
        return self.levels

    def add(self, item: str) -> None:
        with self._lock:
            for f in self.filters:
                f.add(item)

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    def contains(self, item: str) -> bool:
        with self._lock:
            # Must exist in all hierarchical tiers
            for f in self.filters:
                if not f.contains(item):
                    return False
            return True

    def compare_digest(self, other_digest: "HierarchicalBloomFilterDigest") -> List[int]:
        """Compares hierarchical tiers and returns mismatched level indices."""
        mismatches: List[int] = []
        with self._lock:
            for idx, (l_f, r_f) in enumerate(zip(self.filters, other_digest.filters)):
                l_ser = l_f.serialize()
                r_ser = r_f.serialize()
                if l_ser["bits"] != r_ser["bits"] or l_ser["size"] != r_ser["size"]:
                    mismatches.append(idx)
        return mismatches

    def serialize(self) -> Dict[str, Any]:
        with self._lock:
            serialized_tiers = [f.serialize() for f in self.filters]
            return {
                "capacity": self.capacity,
                "error_rate": self.error_rate,
                "levels": self.levels,
                "tiers": serialized_tiers,
            }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "HierarchicalBloomFilterDigest":
        instance = cls(
            capacity=data.get("capacity", 10000), error_rate=data.get("error_rate", 0.01), levels=data.get("levels", 3)
        )
        tiers_data = data.get("tiers", [])
        if tiers_data:
            instance.filters = [BloomFilterDigest.deserialize(t) for t in tiers_data]
            instance.levels = len(instance.filters)
        return instance
