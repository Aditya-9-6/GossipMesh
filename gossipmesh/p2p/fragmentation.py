"""
Packet fragmentation and assembly mechanisms for oversized gossip payloads.
"""

import zlib
from typing import Any, Dict, List, Optional, Tuple


class PacketFragment:
    def __init__(self, message_id: str, index: int, total: int, crc32: int, data: bytes) -> None:
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
    def __init__(self, mtu: int = 1400) -> None:
        self.mtu = mtu

    def fragment(self, message_id: str, payload: bytes) -> List[PacketFragment]:
        full_crc = zlib.crc32(payload) & 0xFFFFFFFF
        chunk_size = max(100, self.mtu - 128)
        chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]
        total = len(chunks)
        return [PacketFragment(message_id, idx, total, full_crc, chunk) for idx, chunk in enumerate(chunks)]


class PacketAssembler:
    def __init__(self, timeout_sec: float = 30.0) -> None:
        self.timeout_sec = timeout_sec
        self.buffers: Dict[str, Dict[str, Any]] = {}

    def add_fragment(self, frag: PacketFragment) -> Optional[bytes]:
        if frag.message_id not in self.buffers:
            self.buffers[frag.message_id] = {
                "total": frag.total,
                "crc32": frag.crc32,
                "fragments": {},
            }
        buf = self.buffers[frag.message_id]
        if buf["total"] != frag.total or buf["crc32"] != frag.crc32:
            return None
        buf["fragments"][frag.index] = frag.data
        if len(buf["fragments"]) == frag.total:
            full_data = b"".join(buf["fragments"][i] for i in range(frag.total))
            del self.buffers[frag.message_id]
            if (zlib.crc32(full_data) & 0xFFFFFFFF) != frag.crc32:
                return None
            return full_data
        return None
