from typing import Any, Dict, List, Optional


class VectorClockEntropy:
    """Anti-entropy synchronizer using vector clocks and Merkle trees."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.vector_clock: Dict[str, int] = {}

    def increment(self) -> Dict[str, int]:
        self.vector_clock[self.node_id] = self.vector_clock.get(self.node_id, 0) + 1
        return self.vector_clock

    def merge(self, remote_clock: Dict[str, int]) -> Dict[str, int]:
        for k, v in remote_clock.items():
            self.vector_clock[k] = max(self.vector_clock.get(k, 0), v)
        return self.vector_clock
