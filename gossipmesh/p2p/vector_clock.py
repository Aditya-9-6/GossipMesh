from typing import Dict, Optional, Any


class VectorClock:
    """Compact vector clock implementation for decentralized peer state tracking."""

    def __init__(self, clock_dict: Optional[Dict[str, int]] = None):
        self.clock: Dict[str, int] = dict(clock_dict) if clock_dict else {}

    def increment(self, node_id: str) -> "VectorClock":
        self.clock[node_id] = self.clock.get(node_id, 0) + 1
        return self

    def update(self, other: "VectorClock") -> "VectorClock":
        for node_id, v in other.clock.items():
            self.clock[node_id] = max(self.clock.get(node_id, 0), v)
        return self

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> "VectorClock":
        return cls(d)

    def clone(self) -> "VectorClock":
        return VectorClock(self.clock)

    def compare(self, other: "VectorClock") -> str:
        """Returns 'concurrent', 'before', 'after', or 'equal'."""
        keys = set(self.clock.keys()).union(set(other.clock.keys()))
        self_greater = False
        other_greater = False

        for k in keys:
            v1 = self.clock.get(k, 0)
            v2 = other.clock.get(k, 0)
            if v1 > v2:
                self_greater = True
            elif v1 < v2:
                other_greater = True

        if self_greater and other_greater:
            return "concurrent"
        if self_greater:
            return "after"
        if other_greater:
            return "before"
        return "equal"
