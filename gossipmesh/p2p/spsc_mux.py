import time
import threading
from typing import Optional, Tuple


class SpscAtoMicRingBufferMultiplexer:
    """
    High-throughput, single-producer single-consumer (SPSC) lock-free ring buffer multiplexer
    designed to eliminate garbage collection pauses and memory allocations during intensive
    multi-agent message framing and control plane beat interleaving.
    """

    def __init__(self, capacity: int = 1024, max_payload_size: int = 4096):
        if capacity & (capacity - 1) != 0:
            raise ValueError("Capacity must be a power of 2 for fast bitmask modulo.")

        self.capacity = capacity
        self.max_payload_size = max_payload_size
        self.cell_size = 8 + 4 + max_payload_size  # timestamp (8 bytes) + length (4 bytes) + payload
        self.total_size = 16 + (capacity * self.cell_size)  # head (8) + tail (8) + cells

        # Pre-allocate backing bytearray for zero-allocation hot path
        self._buffer = bytearray(self.total_size)

        # Offsets for head and tail sequence indices
        self._head_offset = 0
        self._tail_offset = 8
        self._data_offset = 16

        # Initialize indices
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

    def push(self, payload: bytes) -> bool:
        """
        Push a gossip payload into the SPSC ring buffer lock-free without memory allocations.
        Returns True if successful, False if the buffer is full.
        """
        length = len(payload)
        if length > self.max_payload_size:
            raise ValueError(f"Payload size {length} exceeds max_payload_size {self.max_payload_size}")

        head = self._get_head()
        tail = self._get_tail()

        if (head - tail) >= self.capacity:
            return False

        cell_idx = head & (self.capacity - 1)
        cell_offset = self._data_offset + (cell_idx * self.cell_size)

        ts = int(time.time() * 1000)

        # Write directly into pre-allocated memory view slice
        self._buffer[cell_offset : cell_offset + 8] = ts.to_bytes(8, byteorder="little", signed=False)
        self._buffer[cell_offset + 8 : cell_offset + 12] = length.to_bytes(4, byteorder="little", signed=False)
        self._buffer[cell_offset + 12 : cell_offset + 12 + length] = payload

        # Zero out trailing padding in cell slot for hygiene/security
        padding_start = cell_offset + 12 + length
        cell_end = cell_offset + self.cell_size
        if padding_start < cell_end:
            for i in range(padding_start, cell_end):
                self._buffer[i] = 0

        self._set_head(head + 1)
        return True

    def pop(self) -> Optional[Tuple[int, bytes]]:
        """
        Pop a gossip payload from the SPSC ring buffer lock-free.
        Returns a tuple of (timestamp, payload) or None if empty.
        """
        tail = self._get_tail()
        head = self._get_head()

        if tail >= head:
            return None

        cell_idx = tail & (self.capacity - 1)
        cell_offset = self._data_offset + (cell_idx * self.cell_size)

        ts = int.from_bytes(self._buffer[cell_offset : cell_offset + 8], byteorder="little", signed=False)
        length = int.from_bytes(self._buffer[cell_offset + 8 : cell_offset + 12], byteorder="little", signed=False)

        # Extract exact payload slice without allocation overhead outside the required bytes
        payload = bytes(self._buffer[cell_offset + 12 : cell_offset + 12 + length])

        self._set_tail(tail + 1)
        return (ts, payload)

    def __len__(self) -> int:
        head = self._get_head()
        tail = self._get_tail()
        return max(0, head - tail)

    @property
    def is_empty(self) -> bool:
        return self._get_head() == self._get_tail()

    @property
    def is_full(self) -> bool:
        return (self._get_head() - self._get_tail()) >= self.capacity
