import threading
from typing import Optional, List, Dict, Any


class ZeroCopyBufferPool:
    """
    Thread-safe, zero-allocation pre-allocated memory slice pool designed for high-throughput
    P2P gossip transport frames to eliminate GC pressure on hot paths.
    """

    def __init__(self, slice_size: int = 4096, initial_pool_size: int = 256, max_pool_size: int = 4096):
        self.slice_size = slice_size
        self.max_pool_size = max_pool_size
        self._pool: List[bytearray] = [bytearray(slice_size) for _ in range(initial_pool_size)]
        self._lock = threading.Lock()
        self._allocated_count = initial_pool_size

    def acquire(self) -> bytearray:
        """
        Acquire a pre-allocated bytearray slice from the pool. If the pool is empty,
        creates a new slice up to max limit or dynamically if needed.
        """
        with self._lock:
            if self._pool:
                buf = self._pool.pop()
                # Reset slice contents or length view if necessary
                return buf
            else:
                self._allocated_count += 1
                return bytearray(self.slice_size)

    def release(self, buf: bytearray) -> None:
        """
        Return a memory slice back to the pool for reuse, preventing allocations.
        """
        if len(buf) != self.slice_size:
            return
        with self._lock:
            if len(self._pool) < self.max_pool_size:
                # Clear / reset memory if sensitive or needed
                self._pool.append(buf)

    @property
    def available_count(self) -> int:
        with self._lock:
            return len(self._pool)
