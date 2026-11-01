"""Memory-mapped circular ring buffer for zero-copy high-throughput P2P packet transport."""

import mmap
import os
import threading
from typing import Optional


class MMapCircularRingBuffer:
    """Thread-safe, zero-copy circular ring buffer backed by an OS memory-mapped file."""

    def __init__(self, size: int = 65536, backing_file: Optional[str] = None):
        self.size = size
        self._lock = threading.Lock()
        self._head = 0
        self._tail = 0

        if backing_file:
            self._fd = os.open(backing_file, os.O_RDWR | os.O_CREAT, 0o600)
            os.ftruncate(self._fd, size)
            self._mmap = mmap.mmap(self._fd, size)
        else:
            self._fd = None
            self._mmap = mmap.mmap(-1, size)

    def write(self, data: bytes) -> bool:
        d_len = len(data)
        if d_len + 4 > self.size:
            return False

        with self._lock:
            next_tail = (self._tail + d_len + 4) % self.size
            if next_tail == self._head:
                return False  # Buffer full

            # Write length header (4 bytes) and payload using slice assignments for zero-copy speed
            len_bytes = d_len.to_bytes(4, "big")
            if self._tail + 4 <= self.size:
                self._mmap[self._tail : self._tail + 4] = len_bytes
            else:
                split = self.size - self._tail
                self._mmap[self._tail : self.size] = len_bytes[:split]
                self._mmap[0 : 4 - split] = len_bytes[split:]

            payload_pos = (self._tail + 4) % self.size
            if payload_pos + d_len <= self.size:
                self._mmap[payload_pos : payload_pos + d_len] = data
            else:
                split = self.size - payload_pos
                self._mmap[payload_pos : self.size] = data[:split]
                self._mmap[0 : d_len - split] = data[split:]

            self._tail = next_tail
            return True

    def read(self) -> Optional[bytes]:
        with self._lock:
            if self._head == self._tail:
                return None  # Buffer empty

            # Read length header (4 bytes)
            len_bytes = bytearray(4)
            if self._head + 4 <= self.size:
                len_bytes[:] = self._mmap[self._head : self._head + 4]
            else:
                split = self.size - self._head
                len_bytes[:split] = self._mmap[self._head : self.size]
                len_bytes[split:] = self._mmap[0 : 4 - split]

            d_len = int.from_bytes(len_bytes, "big")
            payload_pos = (self._head + 4) % self.size

            # Read payload
            payload = bytearray(d_len)
            if payload_pos + d_len <= self.size:
                payload[:] = self._mmap[payload_pos : payload_pos + d_len]
            else:
                split = self.size - payload_pos
                payload[:split] = self._mmap[payload_pos : self.size]
                payload[split:] = self._mmap[0 : d_len - split]

            self._head = (self._head + d_len + 4) % self.size
            return bytes(payload)

    def close(self) -> None:
        with self._lock:
            if self._mmap:
                self._mmap.close()
            if self._fd is not None:
                os.close(self._fd)
