import sys
import time
import hashlib
from collections import OrderedDict
from typing import Dict, Any, Optional, List


class RetransmissionCache:
    """Fixed-capacity ring-buffer message retransmission cache with strict memory bounds and backpressure signaling."""

    def __init__(self, capacity: int = 1000, max_memory_bytes: int = 16 * 1024 * 1024):
        self.capacity = capacity
        self.max_memory_bytes = max_memory_bytes
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._current_memory = 0

    def _compute_key(self, message_id: str) -> str:
        """Generates a cryptographically secure hash key using SHA-256 to prevent hash flooding/DoS."""
        return hashlib.sha256(message_id.encode("utf-8")).hexdigest()

    def put(self, message_id: str, payload: Dict[str, Any]) -> bool:
        """Stores a message in the ring-buffer cache with strict memory bounding and eviction."""
        key = self._compute_key(message_id)
        serialized = str(payload)
        msg_size = sys.getsizeof(serialized) + sys.getsizeof(key)

        if msg_size > self.max_memory_bytes:
            return False

        if key in self._cache:
            old_payload = self._cache.pop(key)
            self._current_memory -= sys.getsizeof(str(old_payload))

        while (
            len(self._cache) >= self.capacity or (self._current_memory + msg_size) > self.max_memory_bytes
        ) and self._cache:
            _, evicted_val = self._cache.popitem(last=False)
            self._current_memory -= sys.getsizeof(str(evicted_val))

        self._cache[key] = payload
        self._current_memory += msg_size
        return True

    def get(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a message and updates its recency in O(1) time."""
        key = self._compute_key(message_id)
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def check_backpressure(self) -> bool:
        """Returns True if cache utilization exceeds 85%, signaling downstream backpressure."""
        if self.capacity == 0:
            return False
        utilization = len(self._cache) / self.capacity
        memory_utilization = self._current_memory / self.max_memory_bytes if self.max_memory_bytes > 0 else 0.0
        return utilization >= 0.85 or memory_utilization >= 0.85

    def size(self) -> int:
        return len(self._cache)

    def clear(self):
        self._cache.clear()
        self._current_memory = 0
