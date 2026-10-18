import struct
from typing import Tuple

class ZeroCopyPacketParser:
    """Zero-copy packet serialization and parsing utility."""

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        # magic(4) + type(1) + uuid(36) + length(4) = 45 bytes
        uuid_bytes = msg_id.encode('utf-8').ljust(36, b'\x00')[:36]
        length = len(payload)
        header = struct.pack('!BI36sI', msg_type, magic, uuid_bytes, length)
        return header + payload

    @staticmethod
    def parse_header(buf: memoryview, expected_magic: int = 0x474D4553) -> Tuple[int, int, str, int, memoryview]:
        if len(buf) < 45:
            raise ValueError("Buffer too small for header: required 45 bytes")
        
        # Unpack according to serialize_header format '!BI36sI'
        msg_type, magic, uuid_bytes, payload_len = struct.unpack_from('!BI36sI', buf, 0)
        if magic != expected_magic:
            raise ValueError(f"Invalid packet magic: expected {expected_magic:#x}, got {magic:#x}")
        
        msg_id = uuid_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_view = buf[45:45 + payload_len]
        return magic, msg_type, msg_id, payload_len, payload_view
