from typing import Dict, Any

class VectorClock:
    def __init__(self, clock: Dict[str, int] = None):
        self.clock = clock.copy() if clock else {}

    def increment(self, node_id: str) -> None:
        self.clock[node_id] = self.clock.get(node_id, 0) + 1
<<<<<<< HEAD
        return self

    def update(self, other: 'VectorClock') -> 'VectorClock':
        for node_id, val in other.clock.items():
            self.clock[node_id] = max(self.clock.get(node_id, 0), val)
        return self

    def compare(self, other: 'VectorClock') -> str:
        self_keys = set(self.clock.keys())
        other_keys = set(other.clock.keys())
        all_keys = self_keys.union(other_keys)

        self_le_other = True
        other_le_self = True

        for k in all_keys:
            s_val = self.clock.get(k, 0)
            o_val = other.clock.get(k, 0)
            if s_val > o_val:
                self_le_other = False
            if s_val < o_val:
                other_le_self = False

        if self.clock == other.clock:
            return "EQUAL"
        elif self_le_other:
            return "BEFORE"
        elif other_le_self:
            return "AFTER"
        else:
            return "CONCURRENT"
=======
>>>>>>> origin/main

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
