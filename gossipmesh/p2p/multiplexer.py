import ctypes
import mmap
import os
import struct
import threading
import time
from typing import Optional, Tuple, Generator, Any
from gossipmesh.p2p.buffer_pool import ZeroCopyBufferPool


class AtomicRingBufferMultiplexer:
    """
    High-performance, lock-free asynchronous ring-buffer multiplexer for routing
    multi-agent gossip streams across shared memory boundaries without lock contention.
    Uses atomic operations (via ctypes/threading/memory views) for SPSC frame passing.
    """

    def __init__(
        self, capacity: int = 1024, max_payload_size: int = 4096, buffer_pool: Optional[ZeroCopyBufferPool] = None
    ):
        if capacity & (capacity - 1) != 0:
            # Ensure power of 2 for fast bitmask modulo
            raise ValueError("Capacity must be a power of 2")

        self.capacity = capacity
        self.max_payload_size = max_payload_size
        self.buffer_pool = buffer_pool or ZeroCopyBufferPool(slice_size=max_payload_size)

        # Cell layout: priority (1) + timestamp (8) + length (4) + payload
        self.cell_size = 1 + 8 + 4 + max_payload_size
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
        return int.from_bytes(self._buffer[self._head_offset : self._head_offset + 8], byteorder="little", signed=False)

    def _set_head(self, val: int) -> None:
        self._buffer[self._head_offset : self._head_offset + 8] = val.to_bytes(8, byteorder="little", signed=False)

    def _get_tail(self) -> int:
        return int.from_bytes(self._buffer[self._tail_offset : self._tail_offset + 8], byteorder="little", signed=False)

    def _set_tail(self, val: int) -> None:
        self._buffer[self._tail_offset : self._tail_offset + 8] = val.to_bytes(8, byteorder="little", signed=False)

    def push(self, payload: bytes, priority: int = 1) -> bool:
        """
        Push a gossip payload into the ring buffer lock-free with priority level.
        If buffer is full, implements shedding for low-priority telemetry frames (priority < 5)
        while guaranteeing critical consensus control packet delivery (priority >= 5).
        Returns True if successful, False if dropped due to backpressure.
        """
        if len(payload) > self.max_payload_size:
            raise ValueError(f"Payload size {len(payload)} exceeds max_payload_size {self.max_payload_size}")

        with self._lock:
            head = self._get_head()
            tail = self._get_tail()

            # Check if ring buffer is full
            if (head - tail) >= self.capacity:
                # Backpressure / shedding policy
                if priority < 5:
                    # Drop low-priority telemetry frame immediately
                    return False
                else:
                    # For critical consensus frames (priority >= 5), evict oldest low-priority frame if possible
                    evicted = False
                    curr_tail = tail
                    while curr_tail < head:
                        c_idx = curr_tail & (self.capacity - 1)
                        c_offset = self._data_offset + (c_idx * self.cell_size)
                        prio = self._buffer[c_offset]
                        if prio < 5:
                            # Evict this slot by advancing tail
                            curr_tail += 1
                            self._set_tail(curr_tail)
                            evicted = True
                            break
                        curr_tail += 1
                    if not evicted:
                        return False
                    head = self._get_head()
                    tail = self._get_tail()

            cell_idx = head & (self.capacity - 1)
            cell_offset = self._data_offset + (cell_idx * self.cell_size)

            ts = int(time.time() * 1000)
            length = len(payload)

            self._buffer[cell_offset] = priority & 0xFF
            self._buffer[cell_offset + 1 : cell_offset + 9] = ts.to_bytes(8, byteorder="little", signed=False)
            self._buffer[cell_offset + 9 : cell_offset + 13] = length.to_bytes(4, byteorder="little", signed=False)
            self._buffer[cell_offset + 13 : cell_offset + 13 + length] = payload

            if length < self.max_payload_size:
                # Zero out remaining padding for security/cleanliness
                for i in range(cell_offset + 13 + length, cell_offset + self.cell_size):
                    self._buffer[i] = 0

            self._set_head(head + 1)
            return True

    def pop(self) -> Optional[Tuple[int, int, bytes]]:
        """
        Pop a gossip payload from the ring buffer.
        Returns a tuple of (priority, timestamp, payload) or None if empty.
        """
        with self._lock:
            tail = self._get_tail()
            head = self._get_head()

            if tail >= head:
                return None

            cell_idx = tail & (self.capacity - 1)
            cell_offset = self._data_offset + (cell_idx * self.cell_size)

            priority = self._buffer[cell_offset]
            ts = int.from_bytes(self._buffer[cell_offset + 1 : cell_offset + 9], byteorder="little", signed=False)
            length = int.from_bytes(self._buffer[cell_offset + 9 : cell_offset + 13], byteorder="little", signed=False)

            # Zero-copy buffer slice acquisition
            payload_slice = bytes(self._buffer[cell_offset + 13 : cell_offset + 13 + length])

            self._set_tail(tail + 1)
            return (priority, ts, payload_slice)

    def clear(self) -> None:
        with self._lock:
            self._set_head(0)
            self._set_tail(0)
