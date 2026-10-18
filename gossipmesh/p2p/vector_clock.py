from typing import Dict, Any

class VectorClock:
    def __init__(self, clock: Dict[str, int] = None):
        self.clock: Dict[str, int] = dict(clock) if clock else {}

    def increment(self, node_id: str) -> 'VectorClock':
        self.clock[node_id] = self.clock.get(node_id, 0) + 1
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

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'VectorClock':
        return cls(data)

    def __repr__(self) -> str:
        return f"VectorClock({self.clock})"
