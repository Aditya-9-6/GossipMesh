from __future__ import annotations

import time
import zlib
import threading
from typing import Dict, List, Optional, Tuple, Any


class PacketFragment:
    """
    Represents an individual packet fragment for MTU-safe transport.
    """

    def __init__(self, message_id: str, index: int, total: int, crc32: int, data: bytes):
        self.message_id = message_id
        self.index = index
        self.total = total
        self.crc32 = crc32
        self.data = data

    def serialize(self) -> bytes:
        msg_bytes = self.message_id.encode("utf-8")
        header = (
            bytes([len(msg_bytes)])
            + msg_bytes
            + self.index.to_bytes(4, "big")
            + self.total.to_bytes(4, "big")
            + self.crc32.to_bytes(4, "big")
            + len(self.data).to_bytes(4, "big")
        )
        return header + self.data

    @classmethod
    def deserialize(cls, raw: bytes) -> PacketFragment:
        if len(raw) < 17:
            raise ValueError("Fragment payload too short")
        id_len = raw[0]
        if len(raw) < 1 + id_len + 16:
            raise ValueError("Invalid fragment header structure")
        message_id = raw[1 : 1 + id_len].decode("utf-8")
        offset = 1 + id_len
        index = int.from_bytes(raw[offset : offset + 4], "big")
        total = int.from_bytes(raw[offset + 4 : offset + 8], "big")
        crc32 = int.from_bytes(raw[offset + 8 : offset + 12], "big")
        data_len = int.from_bytes(raw[offset + 12 : offset + 16], "big")
        offset += 16
        if len(raw) < offset + data_len:
            raise ValueError("Fragment data length mismatch")
        data = raw[offset : offset + data_len]
        return cls(message_id, index, total, crc32, data)


class PacketFragmenter:
    """
    Splits large packets into MTU-compliant fragments.
    """

    def __init__(self, mtu: int = 1400):
        self.mtu = mtu

    def fragment(self, message_id: str, payload: bytes) -> List[PacketFragment]:
        full_crc = zlib.crc32(payload) & 0xFFFFFFFF
        chunk_size = max(100, self.mtu - 128)
        chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]
        total = len(chunks)
        if total == 0:
            chunks = [b""]
            total = 1
        return [PacketFragment(message_id, i, total, full_crc, chunk) for i, chunk in enumerate(chunks)]


class PacketReassembler:
    """
    Reassembles packet fragments with timeout-based buffer garbage collection.
    """

    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = timeout_sec
        self.buffers: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_fragment(self, frag: PacketFragment) -> Optional[bytes]:
        with self._lock:
            now = time.time()
            self._cleanup_expired(now)

            if frag.message_id not in self.buffers:
                self.buffers[frag.message_id] = {
                    "fragments": {},
                    "total": frag.total,
                    "crc32": frag.crc32,
                    "timestamp": now,
                }

            buf = self.buffers[frag.message_id]
            buf["fragments"][frag.index] = frag.data

            if len(buf["fragments"]) == buf["total"]:
                complete_data = b"".join(buf["fragments"].get(i, b"") for i in range(buf["total"]))
                computed_crc = zlib.crc32(complete_data) & 0xFFFFFFFF
                del self.buffers[frag.message_id]
                if computed_crc != buf["crc32"]:
                    raise ValueError("Reassembled packet CRC32 mismatch")
                return complete_data

            return None

    def _cleanup_expired(self, now: float) -> None:
        expired = [msg_id for msg_id, data in self.buffers.items() if now - data["timestamp"] > self.timeout_sec]
        for msg_id in expired:
            del self.buffers[msg_id]
