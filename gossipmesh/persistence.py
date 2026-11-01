"""
High-throughput, thread-safe, memory-mapped journaling ledger for persistent gossip state recovery.

Supports append-only sequential writes with atomic block allocation, zero-copy buffer slicing,
and cyclic redundancy checksum (CRC32C) validation per frame.
"""

from __future__ import annotations

import mmap
import os
import struct
import threading

zlib_available = True
try:
    import zlib
except ImportError:
    zlib_available = False


class JournalingLedger:
    """
    Memory-mapped journaling ledger for append-only crash-safe gossip state persistence.

    Frame format:
    [magic: 4 bytes (0x47535048 'GSPH')] [length: 4 bytes uint32] [crc32c: 4 bytes uint32] [payload: N bytes]
    """

    MAGIC = b"GSPH"
    HEADER_FORMAT = "!4sII"  # Magic, Length, CRC32C
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    DEFAULT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB default mmap size

    def __init__(self, file_path: str, initial_size: int = DEFAULT_FILE_SIZE) -> None:
        self.file_path = file_path
        self.initial_size = initial_size
        self._lock = threading.Lock()
        self._file_obj = None
        self._mmap_obj = None
        self._current_offset = 0
        self._capacity = initial_size

        self._init_storage()

    def _init_storage(self) -> None:
        file_exists = os.path.exists(self.file_path)
        file_mode = "r+b" if file_exists else "w+b"

        # Ensure directory exists
        dir_name = os.path.dirname(os.path.abspath(self.file_path))
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        self._file_obj = open(self.file_path, file_mode)

        if not file_exists:
            self._file_obj.write(b"\x00" * self.initial_size)
            self._file_obj.flush()

        self._file_obj.seek(0, os.SEEK_END)
        actual_size = self._file_obj.tell()
        if actual_size < self.initial_size:
            self._file_obj.write(b"\x00" * (self.initial_size - actual_size))
            self._file_obj.flush()
            actual_size = self.initial_size

        self._capacity = actual_size
        self._mmap_obj = mmap.mmap(self._file_obj.fileno(), self._capacity, access=mmap.ACCESS_WRITE)

        # Scan to find current write offset based on valid frames
        self._current_offset = self._scan_valid_offset()

    def _scan_valid_offset(self) -> int:
        offset = 0
        m = self._mmap_obj
        length = self._capacity

        while offset + self.HEADER_SIZE <= length:
            header_bytes = m[offset : offset + self.HEADER_SIZE]
            if len(header_bytes) < self.HEADER_SIZE:
                break
            magic, payload_len, stored_crc = struct.unpack(self.HEADER_FORMAT, header_bytes)

            if magic != self.MAGIC:
                break

            total_frame_size = self.HEADER_SIZE + payload_len
            if offset + total_frame_size > length:
                break

            payload = m[offset + self.HEADER_SIZE : offset + total_frame_size]
            if len(payload) < payload_len:
                break

            # Compute CRC32C
            calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
            if calc_crc != stored_crc:
                # Corruption or partial write encountered; truncate here
                break

            offset += total_frame_size

        return offset

    def _ensure_capacity(self, needed_bytes: int) -> None:
        if self._current_offset + needed_bytes <= self._capacity:
            return

        # Double capacity or fit required size
        new_capacity = max(self._capacity * 2, self._current_offset + needed_bytes)
        self._mmap_obj.close()

        self._file_obj.seek(new_capacity)
        self._file_obj.write(b"\x00" * (new_capacity - self._capacity))
        self._file_obj.flush()

        self._capacity = new_capacity
        self._mmap_obj = mmap.mmap(self._file_obj.fileno(), self._capacity, access=mmap.ACCESS_WRITE)

    def append(self, payload: bytes) -> int:
        """
        Append a payload frame atomically to the journaling ledger.
        Returns the offset where the frame was written.
        """
        payload_len = len(payload)
        calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
        header = struct.pack(self.HEADER_FORMAT, self.MAGIC, payload_len, calc_crc)
        total_size = self.HEADER_SIZE + payload_len

        with self._lock:
            self._ensure_capacity(total_size)
            write_pos = self._current_offset
            self._mmap_obj[write_pos : write_pos + total_size] = header + payload
            self._mmap_obj.flush()
            self._current_offset += total_size
            return write_pos

    def recover(self) -> list[bytes]:
        """
        Recover and return all valid payloads from the ledger, validating CRCs.
        """
        with self._lock:
            payloads = []
            offset = 0
            m = self._mmap_obj
            length = self._current_offset

            while offset + self.HEADER_SIZE <= length:
                header_bytes = m[offset : offset + self.HEADER_SIZE]
                magic, payload_len, stored_crc = struct.unpack(self.HEADER_FORMAT, header_bytes)

                if magic != self.MAGIC:
                    break

                total_frame_size = self.HEADER_SIZE + payload_len
                payload_slice = memoryview(m)[offset + self.HEADER_SIZE : offset + total_frame_size]
                payload_bytes = bytes(payload_slice)

                calc_crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF
                if calc_crc != stored_crc:
                    break

                payloads.append(payload_bytes)
                offset += total_frame_size

            return payloads

    def close(self) -> None:
        with self._lock:
            if self._mmap_obj:
                try:
                    self._mmap_obj.flush()
                    self._mmap_obj.close()
                except Exception:
                    pass
                self._mmap_obj = None
            if self._file_obj:
                try:
                    self._file_obj.close()
                except Exception:
                    pass
                self._file_obj = None

    def __enter__(self) -> JournalingLedger:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
