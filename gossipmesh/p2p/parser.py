import struct
from typing import Tuple, Dict, Any

class ZeroCopyPacketParser:
    """Zero-copy parser for gossip wire packets using memoryview and struct unpacking."""
    
    HEADER_FORMAT = "!BI"  # Magic byte (1), Payload length (4)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAGIC_BYTE = 0x47  # 'G'

    @staticmethod
    def parse_header(buffer: memoryview) -> Tuple[int, int]:
        """Parses packet header without allocating new byte strings."""
        if len(buffer) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError("Buffer too small for packet header")
        
        magic, length = struct.unpack_from(ZeroCopyPacketParser.HEADER_FORMAT, buffer, 0)
        if magic != ZeroCopyPacketParser.MAGIC_BYTE:
            raise ValueError(f"Invalid packet magic byte: {hex(magic)}")
        
        return magic, length

    @staticmethod
    def extract_payload(buffer: memoryview, length: int) -> memoryview:
        """Extracts payload zero-copy using memoryview slicing."""
        total_needed = ZeroCopyPacketParser.HEADER_SIZE + length
        if len(buffer) < total_needed:
            raise ValueError("Incomplete packet buffer")
        
        return buffer[ZeroCopyPacketParser.HEADER_SIZE:total_needed]

    @staticmethod
    def serialize_packet(msg_type: bytes, payload_bytes: bytes) -> bytes:
        """Helper to construct valid wire format packets for testing/transport."""
        length = len(payload_bytes)
        header = struct.pack(ZeroCopyPacketParser.HEADER_FORMAT, ZeroCopyPacketParser.MAGIC_BYTE, length)
        return header + payload_bytes
