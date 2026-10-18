import threading
from typing import Dict, List, Tuple, Any, Optional


class MatrixClock:
    """Tracks vector/matrix clocks for decentralized causal ordering across agents."""

    def __init__(self, node_id: str, max_window: int = 1000):
        self.node_id = node_id
        self.max_window = max_window
        self.clock: Dict[str, int] = {node_id: 0}
        self._buffer: List[Tuple[str, Dict[str, int], Any]] = []
        self._lock = threading.Lock()

    def increment(self) -> Dict[str, int]:
        with self._lock:
            self.clock[self.node_id] = self.clock.get(self.node_id, 0) + 1
            return dict(self.clock)

    def get_clock(self) -> Dict[str, int]:
        with self._lock:
            return dict(self.clock)

    def update(self, remote_clock: Dict[str, int]) -> None:
        with self._lock:
            for node, val in remote_clock.items():
                self.clock[node] = max(self.clock.get(node, 0), val)

    def satisfies_causality(self, sender: str, remote_clock: Dict[str, int]) -> bool:
        """Verifies if the remote clock satisfies causal preconditions relative to local state.
        For the sender, remote[sender] must be local[sender] + 1.
        For all other nodes k != sender, remote[k] must be <= local[k]."""
        with self._lock:
            expected = self.clock.get(sender, 0) + 1
            actual = remote_clock.get(sender, 0)
            if actual != expected:
                return False

            for k, val in remote_clock.items():
                if k == sender:
                    continue
                if val > self.clock.get(k, 0):
                    return False
            return True

    def buffer_payload(self, sender: str, remote_clock: Dict[str, int], payload: Any) -> None:
        with self._lock:
            self._buffer.append((sender, remote_clock, payload))
            if len(self._buffer) > self.max_window:
                # Enforce strict bounds by dropping the oldest stale buffered items
                self._buffer.pop(0)

    def poll_deliverable(self) -> List[Any]:
        """Scans the buffer for payloads whose causal dependencies are now satisfied.
        Iteratively drains and releases them until no more payloads can be delivered."""
        deliverable = []
        with self._lock:
            progress = True
            while progress and self._buffer:
                progress = False
                remaining_buffer = []
                for sender, remote_clock, payload in self._buffer:
                    if self.satisfies_causality(sender, remote_clock):
                        # Update local clock with sender's advancement
                        self.clock[sender] = remote_clock.get(sender, self.clock.get(sender, 0) + 1)
                        for k, val in remote_clock.items():
                            self.clock[k] = max(self.clock.get(k, 0), val)
                        deliverable.append(payload)
                        progress = True
                    else:
                        remaining_buffer.append((sender, remote_clock, payload))
                self._buffer = remaining_buffer
        return deliverable
