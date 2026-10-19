<<<<<<< HEAD
from typing import Dict, Optional

class VectorClock:
    """Compact vector clock implementation for decentralized peer state tracking."""
    def __init__(self, clock_dict: Optional[Dict[str, int]] = None):
        self.clock: Dict[str, int] = dict(clock_dict) if clock_dict else {}

    def increment(self, node_id: str) -> 'VectorClock':
        self.clock[node_id] = self.clock.get(node_id, 0) + 1
        return self

    def update(self, other: 'VectorClock') -> 'VectorClock':
        for node_id, v in other.clock.items():
            self.clock[node_id] = max(self.clock.get(node_id, 0), v)
        return self

    def compare(self, other: 'VectorClock') -> str:
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
            return 'concurrent'
        if self_greater:
            return 'after'
        if other_greater:
            return 'before'
        return 'equal'

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    def clone(self) -> 'VectorClock':
        return VectorClock(self.clock)
=======
from typing import Dict, Any

class VectorClock:
    def __init__(self, clock: Dict[str, int] = None):
        self.clock = clock.copy() if clock else {}

    def increment(self, node_id: str) -> None:
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def to_dict(self) -> Dict[str, int]:
        return self.clock.copy()

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> 'VectorClock':
        return cls(d)

    def compare(self, other: 'VectorClock') -> str:
        """
        Compare self with other.
        Returns:
        - "BEFORE" if self < other
        - "AFTER" if self > other
        - "CONCURRENT" if neither is strictly greater
        - "EQUAL" if identical
        """
        keys = set(self.clock.keys()).union(set(other.clock.keys()))
        
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
>>>>>>> origin/main
