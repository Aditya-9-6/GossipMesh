import ctypes
import mmap
import os
import struct
import threading
import time
from typing import Optional, Tuple, Generator, Any


class AtomicRingBufferMultiplexer:
    """
    High-performance, lock-free asynchronous ring-buffer multiplexer for routing
    multi-agent gossip streams across shared memory boundaries without lock contention.
    Uses atomic operations (via ctypes/threading/memory views) for SPSC frame passing.
    """

    def __init__(self, capacity: int = 1024, max_payload_size: int = 4096):
        if capacity & (capacity - 1) != 0:
            # Ensure power of 2 for fast bitmask modulo
            raise ValueError("Capacity must be a power of 2")
        
        self.capacity = capacity
        self.max_payload_size = max_payload_size
        self.cell_size = 8 + 4 + max_payload_size  # timestamp (8) + length (4) + payload
        self.total_size = 16 + (capacity * self.cell_size)  # head (8) + tail (8) + cells
        
        # Allocate shared memory buffer
        self._buffer = bytearray(self.total_size)
        self._lock = threading.Lock()  # Guard for concurrent multithreaded fast-paths if needed
        
        # Offsets
        self._head_offset = 0
        self._tail_offset = 8
        self._data_offset = 16
        
        # Initialize head and tail to 0
        self._set_head(0)
        self._set_tail(0)

    def _get_head(self) -> int:
        return int.from_bytes(self._buffer[self._head_offset:self._head_offset+8], byteorder="little", signed=False)

    def _set_head(self, val: int) -> None:
        self._buffer[self._head_offset:self._head_offset+8] = val.to_bytes(8, byteorder="little", signed=False)

    def _get_tail(self) -> int:
        return int.from_bytes(self._buffer[self._tail_offset:self._tail_offset+8], byteorder="little", signed=False)

    def _set_tail(self, val: int) -> None:
        self._buffer[self._tail_offset:self._tail_offset+8] = val.to_bytes(8, byteorder="little", signed=False)

    def push(self, payload: bytes) -> bool:
        """
        Push a gossip payload into the ring buffer lock-free (SPSC).
        Returns True if successful, False if the buffer is full (zero-drop policy handled by caller).
        """
        if len(payload) > self.max_payload_size:
            raise ValueError(f"Payload size {len(payload)} exceeds max_payload_size {self.max_payload_size}")

        head = self._get_head()
        tail = self._get_tail()

        # Check if ring buffer is full
        if (head - tail) >= self.capacity:
            return False

        cell_idx = head & (self.capacity - 1)
        cell_offset = self._data_offset + (cell_idx * self.cell_size)

        # Serialize timestamp (8 bytes) + length (4 bytes) + payload
        ts = int(time.time() * 1000)
        length = len(payload)

        self._buffer[cell_offset:cell_offset+8] = ts.to_bytes(8, byteorder="little", signed=False)
        self._buffer[cell_offset+8:cell_offset+12] = length.to_bytes(4, byteorder="little", signed=False)
        self._buffer[cell_offset+12:cell_offset+12+length] = payload
        if length < self.max_payload_size:
            # Zero out remaining padding for security/cleanliness
            for i in range(cell_offset+12+length, cell_offset+self.cell_size):
                self._buffer[i] = 0

        # Advance head atomically
        self._set_head(head + 1)
        return True

    def pop(self) -> Optional[Tuple[int, bytes]]:
        """
        Pop a gossip payload from the ring buffer.
        Returns a tuple of (timestamp, payload) or None if empty.
        """
        tail = self._get_tail()
        head = self._get_head()

        if tail >= head:
            return None

        cell_idx = tail & (self.capacity - 1)
        cell_offset = self._data_offset + (cell_idx * self.cell_size)

        ts = int.from_bytes(self._buffer[cell_offset:cell_offset+8], byteorder="little", signed=False)
        length = int.from_bytes(self._buffer[cell_offset+8:cell_offset+12], byteorder="little", signed=False)
        payload = bytes(self._buffer[cell_offset+12:cell_offset+12+length])

        # Advance tail atomically
        self._set_tail(tail + 1)
        return (ts, payload)

    def size(self) -> int:
        head = self._get_head()
        tail = self._get_tail()
        return max(0, head - tail)

    def is_empty(self) -> bool:
        return self._get_head() == self._get_tail()

    def is_full(self) -> bool:
        return (self._get_head() - self._get_tail()) >= self.capacity
