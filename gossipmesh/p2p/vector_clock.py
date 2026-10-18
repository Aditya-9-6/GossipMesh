from typing import Dict, Set, Optional

class VectorClock:
    """Tracks causal relationships between nodes in the P2P network."""

    def __init__(self, clock_dict: Optional[Dict[str, int]] = None):
        self.clock: Dict[str, int] = dict(clock_dict) if clock_dict else {}

    def increment(self, node_id: str):
        self.clock[node_id] = self.clock.get(node_id, 0) + 1

    def to_dict(self) -> Dict[str, int]:
        return dict(self.clock)

    def compare(self, other: 'VectorClock') -> str:
        """
        Compares this vector clock with another.
        Returns:
            - 'EQUAL' if both are identical
            - 'BEFORE' if self happened before other
            - 'AFTER' if self happened after other
            - 'CONCURRENT' if neither happened before the other
        """
        all_keys: Set[str] = set(self.clock.keys()).union(set(other.clock.keys()))
        
        self_less_equal = True
        other_less_equal = True

        for k in all_keys:
            v_self = self.clock.get(k, 0)
            v_other = other.clock.get(k, 0)
            if v_self > v_other:
                other_less_equal = False
            if v_self < v_other:
                self_less_equal = False

        if self_less_equal and other_less_equal:
            return "EQUAL"
        elif self_less_equal:
            return "AFTER"
        elif other_less_equal:
            return "BEFORE"
        else:
            return "CONCURRENT"
