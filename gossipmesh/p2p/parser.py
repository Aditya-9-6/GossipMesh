import struct
from typing import Tuple, Dict, Any, Optional

class ZeroCopyPacketParser:
    """Zero-allocation packet parser utilizing memoryviews and struct unpacking."""
    
    HEADER_FORMAT = "!IB36s"  # Magic (4B), Type (1B), UUID/ID (36B)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    @staticmethod
    def parse_header(buffer: memoryview) -> Tuple[int, int, str, memoryview]:
        """Parses packet header from memoryview without byte string allocation."""
        if len(buffer) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError(f"Buffer too small for header: {len(buffer)} < {ZeroCopyPacketParser.HEADER_SIZE}")
        
        header_view = buffer[:ZeroCopyPacketParser.HEADER_SIZE]
        magic, msg_type, raw_id = struct.unpack(ZeroCopyPacketParser.HEADER_FORMAT, header_view)
        
        msg_id = raw_id.rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_view = buffer[ZeroCopyPacketParser.HEADER_SIZE:]
        return magic, msg_type, msg_id, payload_view

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        """Serializes message header and payload into wire format."""
        padded_id = msg_id.encode('utf-8').ljust(36, b'\x00')[:36]
        header = struct.pack(ZeroCopyPacketParser.HEADER_FORMAT, magic, msg_type, padded_id)
        return header + payload
