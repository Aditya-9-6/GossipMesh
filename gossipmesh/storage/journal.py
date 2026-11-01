"""
Asynchronous Memory-Mapped Journaling Log for Persistent Gossip State Recovery.

Provides high-throughput, zero-copy/low-syscall append-only record persistence with
checksum validation, monotonic sequence tracking, and automatic compaction for node restarts.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import mmap
import os
import struct
import threading
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple


class JournalCorruptionError(Exception):
    """Raised when journal record checksum verification fails or magic bytes are invalid."""

    pass


class JournalLog:
    """
    High-performance asynchronous memory-mapped journaling log.

    Record binary layout:
    - Magic Header (4 bytes): b'GMSH'
    - Sequence Number (8 bytes, uint64)
    - Payload Length (4 bytes, uint32)
    - SHA256 Checksum (32 bytes)
    - Payload Bytes (Variable length JSON UTF-8)
    """

    MAGIC = b"GMSH"
    HEADER_FORMAT = "!4s Q I 32s"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, filepath: str | Path, initial_size: int = 1024 * 1024):
        self.filepath = Path(filepath)
        self.initial_size = initial_size
        self._lock = threading.Lock()
        self._file = None
        self._mmap: Optional[mmap.mmap] = None
        self._file_size = 0
        self._write_offset = 0
        self._next_sequence = 1
        self._open_journal()

    def _open_journal(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        exists = self.filepath.exists()

        if not exists or self.filepath.stat().st_size == 0:
            with open(self.filepath, "wb+") as f:
                f.write(b"\x00" * self.initial_size)
            self._file_size = self.initial_size
        else:
            self._file_size = self.filepath.stat().st_size

        self._file = open(self.filepath, "rb+", buffering=0)
        self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_WRITE)

        # Recover state by scanning existing records
        self._recover_state()

    def _ensure_capacity(self, needed_bytes: int) -> None:
        if self._write_offset + needed_bytes <= self._file_size:
            return

        # Resize strategy: double current size or allocate enough
        new_size = max(self._file_size * 2, self._write_offset + needed_bytes + 1024 * 1024)
        self._mmap.close()
        self._file.close()

        with open(self.filepath, "rb+") as f:
            f.seek(new_size - 1)
            f.write(b"\x00")

        self._file = open(self.filepath, "rb+", buffering=0)
        self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_WRITE)
        self._file_size = new_size

    def _recover_state(self) -> None:
        self._write_offset = 0
        max_seq = 0
        pos = 0
        mmap_len = len(self._mmap)

        while pos + self.HEADER_SIZE <= mmap_len:
            # Check if remaining buffer is padding (zeros)
            header_chunk = self._mmap[pos : pos + self.HEADER_SIZE]
            if len(header_chunk) < self.HEADER_SIZE or header_chunk == b"\x00" * self.HEADER_SIZE:
                break

            try:
                magic, seq, length, checksum = struct.unpack(self.HEADER_FORMAT, header_chunk)
                if magic != self.MAGIC:
                    break

                payload_end = pos + self.HEADER_SIZE + length
                if payload_end > mmap_len:
                    break

                payload = self._mmap[pos + self.HEADER_SIZE : payload_end]
                computed_checksum = hashlib.sha256(payload).digest()
                if computed_checksum != checksum:
                    raise JournalCorruptionError(f"Checksum mismatch at journal offset {pos}")

                if seq > max_seq:
                    max_seq = seq

                pos = payload_end
            except struct.error:
                break

        self._write_offset = pos
        self._next_sequence = max_seq + 1

    def append(self, data: Dict[str, Any]) -> int:
        """Synchronously appends a record to the memory-mapped journal."""
        payload = json.dumps(data, sort_keys=True).encode("utf-8")
        length = len(payload)
        checksum = hashlib.sha256(payload).digest()

        total_record_size = self.HEADER_SIZE + length

        with self._lock:
            self._ensure_capacity(total_record_size)
            seq = self._next_sequence
            self._next_sequence += 1

            header = (
                struct.pack(self.MAGIC, self.HEADER_FORMAT.split()[0], seq, length, checksum)
                if False
                else struct.pack(self.HEADER_FORMAT, self.MAGIC, seq, length, checksum)
            )

            self._mmap[self._write_offset : self._write_offset + self.HEADER_SIZE] = header
            self._write_offset += self.HEADER_SIZE

            self._mmap[self._write_offset : self._write_offset + length] = payload
            self._write_offset += length

            # Flush changes to disk asynchronously/safely
            self._mmap.flush()
            return seq

    async def append_async(self, data: Dict[str, Any]) -> int:
        """Asynchronously appends a record without blocking the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.append, data)

    def replay(self) -> List[Tuple[int, Dict[str, Any]]]:
        """Replays all valid records from the journal log."""
        records = []
        with self._lock:
            pos = 0
            mmap_len = len(self._mmap)
            while pos + self.HEADER_SIZE <= mmap_len:
                header_chunk = self._mmap[pos : pos + self.HEADER_SIZE]
                if len(header_chunk) < self.HEADER_SIZE or header_chunk == b"\x00" * self.HEADER_SIZE:
                    break

                magic, seq, length, checksum = struct.unpack(self.HEADER_FORMAT, header_chunk)
                if magic != self.MAGIC:
                    break

                payload_end = pos + self.HEADER_SIZE + length
                payload = self._mmap[pos + self.HEADER_SIZE : payload_end]

                if hashlib.sha256(payload).digest() != checksum:
                    raise JournalCorruptionError(f"Journal corruption detected at offset {pos}")

                data = json.loads(payload.decode("utf-8"))
                records.append((seq, data))
                pos = payload_end
        return records

    async def replay_async(self) -> AsyncIterator[Tuple[int, Dict[str, Any]]]:
        """Asynchronously yields replayed records."""
        records = await asyncio.get_running_loop().run_in_executor(None, self.replay)
        for record in records:
            yield record

    def compact(self, latest_state: Dict[str, Any]) -> int:
        """Compacts the journal by truncating old entries and writing current state as seq 1."""
        with self._lock:
            if self._mmap:
                self._mmap.close()
            if self._file:
                self._file.close()

            # Write new compacted file
            temp_path = self.filepath.with_suffix(".compact")

            # Create compacted file with just the latest state
            payload = json.dumps(latest_state, sort_keys=True).encode("utf-8")
            length = len(payload)
            checksum = hashlib.sha256(payload).digest()
            header = struct.pack(self.HEADER_FORMAT, self.MAGIC, 1, length, checksum)

            with open(temp_path, "wb") as f:
                f.write(header + payload)

            temp_path.replace(self.filepath)
            self._open_journal()
            return self._next_sequence - 1

    def close(self) -> None:
        with self._lock:
            if self._mmap:
                self._mmap.close()
                self._mmap = None
            if self._file:
                self._file.close()
                self._file = None
