import time
from typing import Dict, List, Optional, Set, Tuple, Any


class VectorClock:
    """Represents a vector clock with bounded history and version tracking."""

    def __init__(self, node_id: str, clock: Optional[Dict[str, int]] = None, max_epochs: int = 1024):
        self.node_id = node_id
        self.clock: Dict[str, int] = dict(clock) if clock else {node_id: 0}
        self.max_epochs = max_epochs

    def increment(self) -> Dict[str, int]:
        """Increments the clock for the local node."""
        current = self.clock.get(self.node_id, 0)
        self.clock[self.node_id] = current + 1
        self.prune()
        return dict(self.clock)

    def update(self, remote_clock: Dict[str, int]) -> None:
        """Merges a remote vector clock into the local clock."""
        for node, version in remote_clock.items():
            self.clock[node] = max(self.clock.get(node, 0), version)
        self.prune()

    def prune(self) -> None:
        """Prunes obsolete vector entries or caps total entries to prevent bloat."""
        if len(self.clock) > self.max_epochs:
            # Retain the local node and the highest version epochs up to max_epochs
            sorted_items = sorted(
                self.clock.items(),
                key=lambda item: item[1],
                reverse=True
            )
            retained: Dict[str, int] = {}
            for node, ver in sorted_items:
                if node == self.node_id or len(retained) < self.max_epochs:
                    retained[node] = ver
            self.clock = retained

    def compare(self, remote_clock: Dict[str, int]) -> str:
        """Compares local clock with a remote clock.
        Returns: 'older', 'newer', 'concurrent', or 'equal'
        """
        all_keys = set(self.clock.keys()).union(set(remote_clock.keys()))
        local_greater = False
        remote_greater = False

        for k in all_keys:
            l_val = self.clock.get(k, 0)
            r_val = remote_clock.get(k, 0)
            if l_val > r_val:
                local_greater = True
            elif l_val < r_val:
                remote_greater = True

        if local_greater and remote_greater:
            return "concurrent"
        elif local_greater:
            return "newer"
        elif remote_greater:
            return "older"
        else:
            return "equal"


class AntiEntropyEngine:
    """Manages state reconciliation and anti-entropy synchronization across peers."""

    def __init__(self, node_id: str, max_epochs: int = 1024):
        self.node_id = node_id
        self.vector_clock = VectorClock(node_id, max_epochs=max_epochs)
        self.peer_clocks: Dict[str, Dict[str, int]] = {}
        self.state_store: Dict[str, Tuple[Any, Dict[str, int], float]] = {}

    def set_state(self, key: str, value: Any) -> Dict[str, int]:
        """Updates local state for a key, incrementing the vector clock."""
        clock_snapshot = self.vector_clock.increment()
        self.state_store[key] = (value, clock_snapshot, time.time())
        return clock_snapshot

    def receive_state(self, key: str, value: Any, remote_node: str, remote_clock: Dict[str, int]) -> bool:
        """Reconciles incoming state from a peer using vector clock causality."""
        self.peer_clocks[remote_node] = remote_clock
        self.vector_clock.update(remote_clock)

        if key not in self.state_store:
            self.state_store[key] = (value, remote_clock, time.time())
            return True

        _, local_clock, _ = self.state_store[key]
        vc = VectorClock(self.node_id, clock=local_clock, max_epochs=self.vector_clock.max_epochs)
        relation = vc.compare(remote_clock)

        if relation in ("older", "concurrent"):
            # Accept newer or concurrent state (LWW or concurrent resolution)
            self.state_store[key] = (value, remote_clock, time.time())
            return True

        return False

    def get_state(self, key: str) -> Optional[Any]:
        """Retrieves the value for a given key if present."""
        item = self.state_store.get(key)
        return item[0] if item else None

    def gc_state(self, max_age_seconds: float = 86400) -> int:
        """Garbage collects stale states older than max_age_seconds."""
        now = time.time()
        expired_keys = [
            k for k, (_, _, timestamp) in self.state_store.items()
            if (now - timestamp) > max_age_seconds
        ]
        for k in expired_keys:
            del self.state_store[k]
        return len(expired_keys)
