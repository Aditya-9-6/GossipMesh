import struct
from typing import Tuple


class ZeroCopyPacketParser:
    """Zero-copy packet parser for zero-allocation wire framing in GossipMesh.
    
    Wire format (28 bytes header + payload):
    - Magic (4 bytes, uint32)
    - Message Type (4 bytes, int32)
    - Message ID / UUID (16 bytes, string or binary uuid)
    - Payload Length (4 bytes, uint32)
    """

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        # Ensure msg_id is exactly 16 bytes (or padded/truncated)
        msg_id_bytes = msg_id.encode('utf-8')[:16].ljust(16, b'\x00')
        payload_len = len(payload)
        return struct.pack(">II16sI", magic, msg_type, msg_id_bytes, payload_len) + payload

    @staticmethod
    def parse_header(buf: memoryview) -> Tuple[int, int, str, int]:
        if len(buf) < 28:
            raise ValueError("Buffer too small for zero-copy packet header (minimum 28 bytes required).")
        
        # Unpack header fields: 4 bytes magic, 4 bytes type, 16 bytes id, 4 bytes length
        magic, msg_type, raw_id, payload_len = struct.unpack_from(">II16sI", buf, 0)
        msg_id = raw_id.rstrip(b'\x00').decode('utf-8', errors='ignore')
        return magic, msg_type, msg_id, payload_len
