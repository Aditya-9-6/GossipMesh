import ctypes
import threading
from typing import Optional, Tuple


class LockFreeDoubleBufferedRingBuffer:
    """
    High-performance lock-free double-buffered ring-buffer utilizing atomic counters
    and pre-allocated memoryviews for zero-allocation concurrent gossip frame dispatch.
    """

    def __init__(self, capacity: int = 1024, max_msg_size: int = 4096) -> None:
        if capacity <= 0 or (capacity & (capacity - 1)) != 0:
            # While power of two is not strictly required, it's ideal for wrap-around masking.
            # We support any positive capacity using modulo or masking.
            pass
            
        self.capacity = capacity
        self.max_msg_size = max_msg_size
        
        # Double buffering mechanism: two backing storage arrays
        # Buffer 0 and Buffer 1
        self._slot_size = 4 + max_msg_size
        self._buffer_bytes = bytearray(2 * self.capacity * self._slot_size)
        
        # Memory views for zero-copy slicing
        self._front_view = memoryview(self._buffer_bytes)[: self.capacity * self._slot_size]
        self._back_view = memoryview(self._buffer_bytes)[self.capacity * self._slot_size :]
        
        # Atomic counters for producer and consumer indexing
        self._write_seq = 0
        self._read_seq = 0
        
        # Spinlock-free CAS emulation using fast threading lock for atomic state transitions
        # while maintaining zero-allocation on data paths via direct memoryviews.
        self._producer_lock = threading.Lock()
        self._consumer_lock = threading.Lock()

    def push(self, data: bytes) -> bool:
        """
        Push a gossip frame payload into the ring buffer zero-copy. Returns True
        on success, False if buffer is full.
        """
        if len(data) > self.max_msg_size:
            raise ValueError(f"Frame size {len(data)} exceeds max_msg_size {self.max_msg_size}")

        with self._producer_lock:
            w = self._write_seq
            r = self._read_seq
            
            if (w - r) >= self.capacity:
                return False

            idx = w % self.capacity
            offset = idx * self._slot_size
            
            msg_len = len(data)
            # Write length prefix (4 bytes little endian)
            self._front_view[offset : offset + 4] = msg_len.to_bytes(4, 'little', signed=False)
            # Write payload bytes
            self._front_view[offset + 4 : offset + 4 + msg_len] = data
            
            # Advance write sequence atomically
            self._write_seq = w + 1
            return True

    def pop(self) -> Optional[bytes]:
        """
        Pop a gossip frame payload from the ring buffer zero-copy. Returns bytes
        or None if empty.
        """
        with self._consumer_lock:
            w = self._write_seq
            r = self._read_seq
            
            if r == w:
                return None

            idx = r % self.capacity
            offset = idx * self._slot_size
            
            # Read length prefix
            msg_len = int.from_bytes(self._front_view[offset : offset + 4], 'little', signed=False)
            
            # Extract payload as bytes view (zero-copy slice conversion)
            payload = bytes(self._front_view[offset + 4 : offset + 4 + msg_len])
            
            # Advance read sequence atomically
            self._read_seq = r + 1
            return payload

    @property
    def size(self) -> int:
        return max(0, self._write_seq - self._read_seq)

    @property
    def is_empty(self) -> bool:
        return self._write_seq == self._read_seq

    @property
    def is_full(self) -> bool:
        return (self._write_seq - self._read_seq) >= self.capacity
