import hashlib
import threading
from typing import Any, Dict, Optional


class GossipDedupFilter:
    """High-performance bounded ring-buffer deduplication filter using cryptographic hash truncation.
    
    Prevents amplification storms in dense multi-agent meshes with O(1) time complexity lookups,
    zero memory allocations on steady-state lookups, and thread-safe operations via fine-grained locking.
    """

    def __init__(self, capacity: int = 10000) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be greater than zero.")
        self._capacity = capacity
        self._buffer: list[Optional[bytes]] = [None] * capacity
        self._set: set[bytes] = set()
        self._head = 0
        self._tail = 0
        self._size = 0
        self._lock = threading.Lock()
        
        # Telemetry metrics
        self._duplicates_filtered = 0
        self._total_evaluated = 0

    def _compute_digest(self, frame: bytes) -> bytes:
        """Computes a truncated cryptographic hash of the incoming gossip frame.
        
        Using SHA-256 truncated to 16 bytes for compact storage and minimal collision risk.
        """
        return hashlib.sha256(frame).digest()[:16]

    def is_duplicate(self, frame: bytes) -> bool:
        """Checks if a gossip frame is a duplicate without inserting it.
        
        Performs cryptographic digest computation outside the critical section or safely within.
        """
        digest = self._compute_digest(frame)
        with self._lock:
            return digest in self._set

    def check_and_add(self, frame: bytes) -> bool:
        """Evaluates a gossip frame, returning True if it is a duplicate (already seen),
        or recording it and returning False if it is novel.
        
        Maintains a fixed-size ring buffer with O(1) amortized time complexity.
        """
        digest = self._compute_digest(frame)
        
        with self._lock:
            self._total_evaluated += 1
            if digest in self._set:
                self._duplicates_filtered += 1
                return True

            # If buffer is at capacity, evict the oldest item
            if self._size >= self._capacity:
                oldest_digest = self._buffer[self._tail]
                if oldest_digest is not None:
                    self._set.remove(oldest_digest)
                self._tail = (self._tail + 1) % self._capacity
                self._size -= 1

            # Insert new digest
            self._buffer[self._head] = digest
            self._set.add(digest)
            self._head = (self._head + 1) % self._capacity
            self._size += 1

            return False

    def clear(self) -> None:
        """Resets the deduplication buffer and internal state."""
        with self._lock:
            self._buffer = [None] * self._capacity
            self._set.clear()
            self._head = 0
            self._tail = 0
            self._size = 0
            self._duplicates_filtered = 0
            self._total_evaluated = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Returns telemetry metrics for the deduplication filter."""
        with self._lock:
            return {
                "capacity": self._capacity,
                "current_size": self._size,
                "total_evaluated": self._total_evaluated,
                "duplicates_filtered": self._duplicates_filtered,
                "hit_ratio": (
                    self._duplicates_filtered / self._total_evaluated
                    if self._total_evaluated > 0
                    else 0.0
                ),
            }
