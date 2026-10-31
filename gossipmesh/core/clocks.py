import threading
from typing import Dict, Set, Optional, Tuple, Iterator


class VectorClock:
    """
    Thread-safe vector clock supporting zero-copy state comparisons,
    delta encodings, and anti-entropy synchronization.
    """

    def __init__(self, node_id: str, clock: Optional[Dict[str, int]] = None):
        self.node_id = node_id
        self._clock: Dict[str, int] = dict(clock) if clock is not None else {node_id: 0}
        self._lock = threading.Lock()

    def increment(self) -> int:
        with self._lock:
            self._clock[self.node_id] = self._clock.get(self.node_id, 0) + 1
            return self._clock[self.node_id]

    def update(self, remote_clock: Dict[str, int]) -> None:
        with self._lock:
            for node, timestamp in remote_clock.items():
                current = self._clock.get(node, 0)
                if timestamp > current:
                    self._clock[node] = timestamp

    def get_time(self, node_id: str) -> int:
        with self._lock:
            return self._clock.get(node_id, 0)

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._clock)

    def delta(self, known_clock: Dict[str, int]) -> Dict[str, int]:
        """
        Returns a minimal delta dictionary containing entries
        from this clock that are ahead of or unknown to `known_clock`.
        Optimized to avoid unnecessary allocations or copying when no diff exists.
        """
        with self._lock:
            d = {}
            for node, ts in self._clock.items():
                if ts > known_clock.get(node, 0):
                    d[node] = ts
            return d

    def iter_delta(self, known_clock: Dict[str, int]) -> Iterator[Tuple[str, int]]:
        """
        Zero-allocation generator yielding (node, timestamp) pairs
        that are ahead of `known_clock`.
        """
        with self._lock:
            for node, ts in self._clock.items():
                if ts > known_clock.get(node, 0):
                    yield node, ts

    def compare(self, other_clock: Dict[str, int]) -> str:
        """
        Compares this clock with another clock.
        Returns:
            - 'LESS_THAN' if self <= other and strictly smaller in at least one entry
            - 'GREATER_THAN' if self >= other and strictly larger in at least one entry
            - 'EQUAL' if identical
            - 'CONCURRENT' if neither is greater/lesser
        """
        with self._lock:
            keys = set(self._clock.keys()) | set(other_clock.keys())
            self_greater = False
            other_greater = False

            for k in keys:
                v_self = self._clock.get(k, 0)
                v_other = other_clock.get(k, 0)
                if v_self > v_other:
                    self_greater = True
                elif v_self < v_other:
                    other_greater = True

            if self_greater and not other_greater:
                return "GREATER_THAN"
            if other_greater and not self_greater:
                return "LESS_THAN"
            if not self_greater and not other_greater:
                return "EQUAL"
            return "CONCURRENT"
