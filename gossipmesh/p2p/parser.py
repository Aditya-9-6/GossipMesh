import struct
from typing import Tuple

class ZeroCopyPacketParser:
    """Zero-copy packet parser for GossipMesh wire protocol."""

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        # Wire format: !I (magic) I (msg_type) 32s (msg_id padded) Q (payload_len)
        msg_id_bytes = msg_id.encode('utf-8')[:32].ljust(32, b'\x00')
        payload_len = len(payload)
        header = struct.pack('!II32sQ', magic, msg_type, msg_id_bytes, payload_len)
        return header + payload

    @staticmethod
    def deserialize_header(header_bytes: bytes) -> Tuple[int, int]:
        if len(header_bytes) < 44:
            raise ValueError("Header bytes too short for deserialization.")
        unpacked = struct.unpack('!II32sQ', header_bytes)
        return unpacked[0], unpacked[1]

    @staticmethod
    def parse_header(buf: memoryview) -> Tuple[int, int, str, int, memoryview]:
        if len(buf) < 44:
            raise ValueError(f"Buffer too small for packet header: got {len(buf)} bytes, required 44")
        header_bytes = bytes(buf[:44])
        unpacked = struct.unpack('!II32sQ', header_bytes)
        magic = unpacked[0]
        msg_type = unpacked[1]
        msg_id = unpacked[2].rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_len = unpacked[3]

        if len(buf) < 44 + payload_len:
            raise ValueError(f"Buffer truncated: expected payload length {payload_len}, remaining buffer {len(buf) - 44}")

        payload_view = buf[44:44 + payload_len]
        return magic, msg_type, msg_id, payload_len, payload_view
