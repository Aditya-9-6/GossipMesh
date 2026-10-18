import struct
import uuid
from typing import Tuple

class ZeroCopyPacketParser:
    """Zero-copy packet serialization and deserialization for wire protocols."""
    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        try:
            uid_bytes = uuid.UUID(msg_id).bytes
        except Exception:
            uid_bytes = msg_id.encode('utf-8')[:16].ljust(16, b'\x00')
        if len(uid_bytes) < 36:
            uid_bytes = uid_bytes.ljust(36, b'\x00')
        payload_len = len(payload)
        # magic (4 bytes), msg_type (4 bytes), msg_id (36 bytes), payload_len (4 bytes)
        header = struct.pack(">II 36s I", magic, msg_type, uid_bytes, payload_len)
        return header + payload

    @staticmethod
    def deserialize_header(header_data: bytes) -> Tuple[int, int, bytes, int]:
        if len(header_data) < 48:
            raise ValueError("Header data too short")
        magic, msg_type, msg_id_bytes, payload_len = struct.unpack(">II 36s I", header_data[:48])
        return magic, msg_type, msg_id_bytes, payload_len

    @staticmethod
    def parse_header(header_data: bytes) -> Tuple[int, int, bytes, int]:
        return ZeroCopyPacketParser.deserialize_header(header_data)
