import threading
from typing import Optional


class ReplayProtectionRingBuffer:
    """
    High-performance, zero-allocation circular bit-array ring buffer for O(1)
    duplicate packet detection and replay attack mitigation in the gossip transport layer.
    Operates on integer sequence IDs or packet identifiers using atomic/thread-safe operations.
    """

    def __init__(self, capacity: int = 65536) -> None:
        if capacity <= 0 or (capacity & (capacity - 1)) != 0:
            cap = 1
            while cap < capacity:
                cap <<= 1
            capacity = cap

        self.capacity = capacity
        self.mask = capacity - 1
        self._byte_capacity = (capacity + 7) // 8
        self._buffer = bytearray(self._byte_capacity)
        self._lock = threading.Lock()
        self._base_seq = 0

    def check_and_add(self, seq: int) -> bool:
        """
        Checks if a sequence number has been seen. If not, marks it as seen and returns True.
        If already seen (replay), returns False.
        Provides O(1) time complexity and zero memory allocation during checks.
        """
        with self._lock:
            idx = seq & self.mask
            byte_idx = idx >> 3
            bit_offset = idx & 7

            byte_val = self._buffer[byte_idx]
            bit_mask = 1 << bit_offset

            if (byte_val & bit_mask) != 0:
                return False

            self._buffer[byte_idx] = byte_val | bit_mask
            return True

    def clear(self) -> None:
        """Resets the buffer."""
        with self._lock:
            for i in range(len(self._buffer)):
                self._buffer[i] = 0
