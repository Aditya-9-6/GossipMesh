import time
import threading
from collections import deque
from typing import Dict, List, Optional, Any

class MatrixClockMessage:
    def __init__(
        self,
        sender_id: str,
        message_id: str,
        matrix_clock: Dict[str, int],
        payload: Dict[str, Any],
        timestamp: Optional[float] = None,
    ):
        self.sender_id = sender_id
        self.message_id = message_id
        self.matrix_clock = matrix_clock
        self.payload = payload
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "message_id": self.message_id,
            "matrix_clock": self.matrix_clock,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MatrixClockMessage':
        return cls(
            sender_id=data["sender_id"],
            message_id=data["message_id"],
            matrix_clock=data["matrix_clock"],
            payload=data["payload"],
            timestamp=data.get("timestamp", time.time()),
        )


class BoundedMatrixClockEngine:
    """Bounded matrix-clock reconstruction engine for tracking causal dependencies
    across decentralized multi-agent streams. Buffers out-of-order payloads in a
    zero-allocation circular buffer and releases them strictly when causal
    preconditions are satisfied.
    """
    def __init__(
        self,
        node_id: str,
        max_buffer_size: int = 1000,
        staleness_window_seconds: float = 300.0,
    ):
        self.node_id = node_id
        self.max_buffer_size = max_buffer_size
        self.staleness_window_seconds = staleness_window_seconds
        
        self._lock = threading.Lock()
        self._matrix: Dict[str, Dict[str, int]] = {node_id: {}}
        self._buffer: deque[MatrixClockMessage] = deque(maxlen=max_buffer_size)

    def get_matrix(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            return {k: dict(v) for k, v in self._matrix.items()}

    def increment(self) -> Dict[str, int]:
        with self._lock:
            if self.node_id not in self._matrix:
                self._matrix[self.node_id] = {}
            current = self._matrix[self.node_id].get(self.node_id, 0)
            self._matrix[self.node_id][self.node_id] = current + 1
            return dict(self._matrix[self.node_id])

    def _is_causally_ready(self, msg: MatrixClockMessage) -> bool:
        sender = msg.sender_id
        msg_clock = msg.matrix_clock

        for k, req_val in msg_clock.items():
            if k == sender:
                known_val = self._matrix.get(sender, {}).get(sender, 0)
                if req_val != known_val + 1:
                    return False
            else:
                known_val = self._matrix.get(sender, {}).get(k, 0)
                if req_val > known_val:
                    return False
        return True

    def _update_matrix(self, msg: MatrixClockMessage):
        sender = msg.sender_id
        msg_clock = msg.matrix_clock

        if sender not in self._matrix:
            self._matrix[sender] = {}

        for k, val in msg_clock.items():
            current = self._matrix[sender].get(k, 0)
            if val > current:
                self._matrix[sender][k] = val

        if self.node_id not in self._matrix[sender]:
            self._matrix[sender][self.node_id] = 0

        self._matrix[sender][sender] = msg_clock.get(sender, self._matrix[sender].get(sender, 0))

    def ingest(self, msg: MatrixClockMessage) -> List[MatrixClockMessage]:
        with self._lock:
            now = time.time()
            while self._buffer and (now - self._buffer[0].timestamp > self.staleness_window_seconds):
                self._buffer.popleft()

            self._buffer.append(msg)
            
            released: List[MatrixClockMessage] = []
            progress = True

            while progress:
                progress = False
                temp_buffer: deque[MatrixClockMessage] = deque()
                while self._buffer:
                    m = self._buffer.popleft()
                    if self._is_causally_ready(m):
                        self._update_matrix(m)
                        released.append(m)
                        progress = True
                    else:
                        temp_buffer.append(m)
                self._buffer = temp_buffer

            return released

    def prune_stale(self) -> int:
        with self._lock:
            now = time.time()
            initial_len = len(self._buffer)
            active_buffer = deque(
                (m for m in self._buffer if now - m.timestamp <= self.staleness_window_seconds),
                maxlen=self.max_buffer_size,
            )
            self._buffer = active_buffer
            return initial_len - len(self._buffer)
