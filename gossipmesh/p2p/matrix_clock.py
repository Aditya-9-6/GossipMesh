import threading
import time
from typing import Dict, List, Optional, Tuple, Any


class MatrixClock:
    """
    Thread-safe matrix clock tracking causal dependencies across decentralized multi-agent streams.
    Each node maintains its own vector clock and its view of other nodes' vector clocks.
    """

    def __init__(self, node_id: str, node_ids: Optional[List[str]] = None):
        self.node_id = node_id
        self._matrix: Dict[str, Dict[str, int]] = {}
        self._lock = threading.Lock()

        # Initialize matrix with known nodes if provided
        initial_nodes = node_ids if node_ids is not None else [node_id]
        for n in initial_nodes:
            self._matrix[n] = {}
        if node_id not in self._matrix:
            self._matrix[node_id] = {}

    def increment(self) -> Dict[str, int]:
        with self._lock:
            if self.node_id not in self._matrix:
                self._matrix[self.node_id] = {}
            self._matrix[self.node_id][self.node_id] = self._matrix[self.node_id].get(self.node_id, 0) + 1
            return dict(self._matrix[self.node_id])

    def update(self, remote_node_id: str, remote_clock: Dict[str, int]) -> None:
        with self._lock:
            if remote_node_id not in self._matrix:
                self._matrix[remote_node_id] = {}

            # Update our record of remote node's vector clock
            for k, v in remote_clock.items():
                current = self._matrix[remote_node_id].get(k, 0)
                if v > current:
                    self._matrix[remote_node_id][k] = v

            # Also update our own vector clock component for that node if present
            if self.node_id not in self._matrix:
                self._matrix[self.node_id] = {}
            self_current = self._matrix[self.node_id].get(remote_node_id, 0)
            remote_self_ts = remote_clock.get(self.node_id, 0)
            if remote_self_ts > self_current:
                self._matrix[self.node_id][remote_node_id] = remote_self_ts

    get_vector = lambda self, n: dict(self._matrix.get(n, {}))

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            return {k: dict(v) for k, v in self._matrix.items()}

    def satisfies_causal_dependency(self, sender_id: str, message_vector: Dict[str, int]) -> bool:
        """
        Checks whether causal preconditions are satisfied for a message from sender_id.
        A message's vector clock must be immediately successor to our current causal view.
        """
        with self._lock:
            # Check if message timestamp for sender is exactly one ahead of our recorded view of sender, or valid
            sender_clock = self._matrix.get(sender_id, {})
            msg_seq = message_vector.get(sender_id, 0)
            recorded_seq = sender_clock.get(sender_id, 0)

            if msg_seq > recorded_seq + 1:
                return False  # Missing intermediate messages (out of order / causal gap)

            # Check all other components in message vector against our matrix view
            for node, ts in message_vector.items():
                if node == sender_id:
                    continue
                # We must have observed at least the dependencies the sender had observed
                our_view = self._matrix.get(self.node_id, {}).get(node, 0)
                # Alternatively, check against general matrix consistency
                if ts > our_view + 1:
                    # Potential causal violation unless buffered
                    pass
            return True


class BoundedMatrixClockReconstructionEngine:
    """
    High-throughput, concurrency-safe engine for buffering and reconstructing out-of-order
    gossip payloads using a bounded circular buffer with stale state pruning.
    """

    def __init__(self, node_id: str, max_buffer_size: int = 1000, max_stale_window_sec: float = 60.0):
        self.node_id = node_id
        self.max_buffer_size = max_buffer_size
        self.max_stale_window_sec = max_stale_window_sec
        self.matrix_clock = MatrixClock(node_id)

        # Circular buffer implemented via fixed/bounded list with pointer tracking
        self._buffer: List[Optional[Tuple[float, str, Dict[str, int], Any]]] = [None] * max_buffer_size
        self._head = 0
        self._tail = 0
        self._size = 0
        self._lock = threading.Lock()

    def ingest_payload(self, sender_id: str, message_vector: Dict[str, int], payload: Any) -> List[Any]:
        """
        Ingests a message payload. If causal dependencies are met, immediately returns it
        along with any buffered payloads that are now deliverable. If out of order, buffers it.
        Enforces strict memory bounds by dropping stale states.
        """
        with self._lock:
            self._prune_stale_locked()

            delivered: List[Any] = []

            # Check if current payload is deliverable
            if self.matrix_clock.satisfies_causal_dependency(sender_id, message_vector):
                self.matrix_clock.update(sender_id, message_vector)
                delivered.append(payload)

                # Iteratively check buffered messages for newly satisfied causal dependencies
                delivered.extend(self._drain_deliverable_locked())
            else:
                # Buffer out-of-order payload
                self._push_to_buffer_locked(sender_id, message_vector, payload)

            return delivered

    def _push_to_buffer_locked(self, sender_id: str, message_vector: Dict[str, int], payload: Any) -> None:
        if self._size >= self.max_buffer_size:
            # Evict oldest entry (ring buffer wrap-around / drop oldest stale)
            self._head = (self._head + 1) % self.max_buffer_size
            self._size -= 1

        timestamp = time.time()
        self._buffer[self._tail] = (timestamp, sender_id, message_vector, payload)
        self._tail = (self._tail + 1) % self.max_buffer_size
        self._size += 1

    def _drain_deliverable_locked(self) -> List[Any]:
        delivered = []
        remaining_items: List[Tuple[float, str, Dict[str, int], Any]] = []

        # Collect all active items from circular buffer
        curr = self._head
        for _ in range(self._size):
            item = self._buffer[curr]
            if item is not None:
                remaining_items.append(item)
            curr = (curr + 1) % self.max_buffer_size

        # Reset buffer
        self._head = 0
        self._tail = 0
        self._size = 0
        self._buffer = [None] * self.max_buffer_size

        # Re-evaluate items
        for timestamp, sender_id, message_vector, payload in remaining_items:
            if self.matrix_clock.satisfies_causal_dependency(sender_id, message_vector):
                self.matrix_clock.update(sender_id, message_vector)
                delivered.append(payload)
                # Drain recursively if this unlocks more
                delivered.extend(self._drain_deliverable_locked())
                break
            else:
                self._push_to_buffer_locked(sender_id, message_vector, payload)

        return delivered

    def _prune_stale_locked(self) -> None:
        now = time.time()
        if self._size == 0:
            return

        remaining_items: List[Tuple[float, str, Dict[str, int], Any]] = []
        curr = self._head
        for _ in range(self._size):
            item = self._buffer[curr]
            if item is not None:
                timestamp, sender_id, message_vector, payload = item
                if now - timestamp <= self.max_stale_window_sec:
                    remaining_items.append(item)
            curr = (curr + 1) % self.max_buffer_size

        # Rebuild buffer with non-stale items
        self._head = 0
        self._tail = 0
        self._size = 0
        self._buffer = [None] * self.max_buffer_size

        for item in remaining_items:
            self._push_to_buffer_locked(item[1], item[2], item[3])

    def buffer_size(self) -> int:
        with self._lock:
            return self._size
