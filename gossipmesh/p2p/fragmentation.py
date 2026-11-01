import zlib
import struct
from typing import Dict, Optional, List, Any


class PacketFragment:
    def __init__(
        self,
        message_id: str,
        fragment_index: int,
        total_fragments: int,
        payload: bytes,
        crc32: int,
    ):
        self.message_id = message_id
        self.fragment_index = fragment_index
        self.total_fragments = total_fragments
        self.payload = payload
        self.crc32 = crc32

    def serialize(self) -> bytes:
        msg_bytes = self.message_id.encode("utf-8")
        header = struct.pack(
            "!H 32s H H I", len(msg_bytes), msg_bytes, self.fragment_index, self.total_fragments, self.crc32
        )
        return header + self.payload

    @classmethod
    def deserialize(cls, data: bytes) -> "PacketFragment":
        (msg_len,) = struct.unpack("!H", data[0:2])
        msg_id_bytes, frag_idx, total_frags, crc = struct.unpack("!32s H H I", data[2 : 2 + 32 + 8])
        message_id = msg_id_bytes[:msg_len].decode("utf-8")
        payload = data[2 + 32 + 8 :]
        return cls(message_id, frag_idx, total_frags, payload, crc)


class PacketFragmenter:
    def __init__(self, mtu: int = 1200):
        self.mtu = max(100, mtu)

    def fragment(self, message_id: str, payload: bytes) -> List[PacketFragment]:
        crc = zlib.crc32(payload)
        header_overhead = 44
        chunk_size = max(20, self.mtu - header_overhead)
        chunks = [payload[i : i + chunk_size] for i in range(0, len(payload), chunk_size)]
        total = len(chunks)
        return [
            PacketFragment(
                message_id=message_id,
                fragment_index=idx,
                total_fragments=total,
                payload=chunk,
                crc32=crc,
            )
            for idx, chunk in enumerate(chunks)
        ]


class PacketReassembler:
    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = timeout_sec
        self.buffers: Dict[str, Dict[str, Any]] = {}

    def add_fragment(self, frag: PacketFragment) -> Optional[bytes]:
        msg_id = frag.message_id
        if msg_id not in self.buffers:
            self.buffers[msg_id] = {
                "total": frag.total_fragments,
                "frags": {},
                "crc32": frag.crc32,
            }

        buf = self.buffers[msg_id]
        buf["frags"][frag.fragment_index] = frag.payload

        if len(buf["frags"]) == buf["total"]:
            sorted_chunks = [buf["frags"][i] for i in range(buf["total"])]
            full_payload = b"".join(sorted_chunks)
            if zlib.crc32(full_payload) != buf["crc32"]:
                raise ValueError(f"CRC32 checksum mismatch for message {msg_id}")
            del self.buffers[msg_id]
            return full_payload

        return None
