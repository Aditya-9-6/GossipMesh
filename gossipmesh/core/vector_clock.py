from typing import Dict, Optional, Any

class VectorClock:
    """Vector clock implementation for tracking causal ordering in distributed mesh nodes."""
    
    def __init__(self, clock_dict: Optional[Dict[str, int]] = None):
        self.clock: Dict[str, int] = dict(clock_dict) if clock_dict else {}

    def increment(self, node_id: str) -> 'VectorClock':
        new_clock = dict(self.clock)
        new_clock[node_id] = new_clock.get(node_id, 0) + 1
        return VectorClock(new_clock)

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        merged = dict(self.clock)
        for node, val in other.clock.items():
            merged[node] = max(merged.get(node, 0), val)
        return VectorClock(merged)

    def compare(self, other: 'VectorClock') -> str:
        """
        Compares two vector clocks.
        Returns:
            'LESS_THAN': self is causally before other
            'GREATER_THAN': self is causally after other
            'CONCURRENT': concurrent/conflicting mutation paths
            'EQUAL': identical clocks
        """
        keys = set(self.clock.keys()).union(set(other.clock.keys()))
        
        self_less_or_equal = True
        other_less_or_equal = True

        for k in keys:
            v_self = self.clock.get(k, 0)
            v_other = other.clock.get(k, 0)
            if v_self > v_other:
                other_less_or_equal = False
            if v_self < v_other:
                self_less_or_equal = False

        if self_less_or_equal and other_less_or_equal:
            return 'EQUAL'
        elif self_less_or_equal:
            return 'LESS_THAN'
        elif other_less_or_equal:
            return 'GREATER_THAN'
        else:
            return 'CONCURRENT'

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'VectorClock':
        return cls(data)

    def __repr__(self) -> str:
        return f"VectorClock({self.clock})"
