from __future__ import annotations
from typing import Dict, Any, Set


class VectorClock:
    def __init__(self, clock: Dict[str, int] = None) -> None:
        self.clock: Dict[str, int] = clock.copy() if clock else {}

    def increment(self, node_id: str) -> None:
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def to_dict(self) -> Dict[str, int]:
        return self.clock.copy()

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> VectorClock:
        return cls(d)

    def compare(self, other: VectorClock) -> str:
        keys: Set[str] = set(self.clock.keys()).union(set(other.clock.keys()))
        less_or_equal = True
        greater_or_equal = True

        for k in keys:
            v_self = self.clock.get(k, 0)
            v_other = other.clock.get(k, 0)
            if v_self > v_other:
                less_or_equal = False
            if v_self < v_other:
                greater_or_equal = False

        if self.clock == other.clock:
            return "EQUAL"
        if less_or_equal:
            return "BEFORE"
        if greater_or_equal:
            return "AFTER"
        return "CONCURRENT"

    def compact(self, max_entries: int = 100, prune_threshold: int = 1000) -> None:
        """Bounds memory overhead by compacting stale causal trees if max capacity is exceeded."""
        if len(self.clock) <= max_entries:
            return
        # Keep highest values or sort by value and prune lowest
        sorted_items = sorted(self.clock.items(), key=lambda x: x[1], reverse=True)
        self.clock = dict(sorted_items[:max_entries])
