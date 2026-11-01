"""
Adaptive Packet Fragmentation and Reassembly with CRC32 Validation for GossipMesh P2P transport.
Provides MTU-safe chunking, sequence numbering, CRC32 error checking, and sliding window reassembly.
"""

import zlib
import time
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PacketFragment:
    def __init__(self, message_id: str, index: int, total: int, crc32: int, data: bytes):
        self.message_id = message_id
        self.index = index
        self.total = total
        self.crc32 = crc32
        self.data = data

    def serialize(self) -> bytes:
        # Simple header format: msg_id_len (1B), msg_id, index (4B), total (4B), crc32 (4B), data_len (4B), data
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
    def deserialize(cls, raw: bytes) -> "PacketFragment":
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
    def __init__(self, mtu: int = 1400):
        self.mtu = mtu

    def fragment(self, message_id: str, payload: bytes) -> List[PacketFragment]:
        full_crc = zlib.crc32(payload) & 0xFFFFFFFF
        # Reserve space for header overhead
        chunk_size = max(100, self.mtu - 128)
        chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]
        total = len(chunks)
        if total == 0:
            chunks = [b""]
            total = 1
        return [PacketFragment(message_id, i, total, full_crc, chunk) for i, chunk in enumerate(chunks)]


class PacketReassembler:
    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = timeout_sec
        self.buffers: Dict[str, Dict[str, Any]] = {}

    def add_fragment(self, frag: PacketFragment) -> Optional[bytes]:
        self._gc()
        now = time.time()
        if frag.message_id not in self.buffers:
            self.buffers[frag.message_id] = {
                "fragments": {},
                "total": frag.total,
                "crc32": frag.crc32,
                "timestamp": now,
            }
        buf = self.buffers[frag.message_id]
        if buf["total"] != frag.total or buf["crc32"] != frag.crc32:
            logger.warning(f"Fragment metadata mismatch for message {frag.message_id}")
            return None

        buf["fragments"][frag.index] = frag.data
        if len(buf["fragments"]) == buf["total"]:
            complete_data = b"".join(buf["fragments"][i] for i in range(buf["total"]))
            computed_crc = zlib.crc32(complete_data) & 0xFFFFFFFF
            del self.buffers[frag.message_id]
            if computed_crc != frag.crc32:
                logger.error(f"CRC32 validation failed for reassembled message {frag.message_id}")
                raise ValueError("CRC32 checksum mismatch on reassembled packet")
            return complete_data
        return None

    def _gc(self):
        now = time.time()
        expired = [mid for mid, b in self.buffers.items() if now - b["timestamp"] > self.timeout_sec]
        for mid in expired:
            del self.buffers[mid]
