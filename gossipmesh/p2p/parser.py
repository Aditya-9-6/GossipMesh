import struct
<<<<<<< HEAD
from typing import Tuple, Dict, Any

class ZeroCopyPacketParser:
    """Zero-copy parser for gossip wire packets using memoryview and struct unpacking."""
    
    HEADER_FORMAT = "!BI"  # Magic byte (1), Payload length (4)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAGIC_BYTE = 0x47  # 'G'
    MAX_PAYLOAD_LENGTH = 16 * 1024 * 1024  # 16 MB max safety limit

    @staticmethod
    def parse_header(buffer: memoryview) -> Tuple[int, int]:
        """Parses packet header without allocating new byte strings."""
        if len(buffer) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError("Buffer too small for packet header")
        
        magic, length = struct.unpack_from(ZeroCopyPacketParser.HEADER_FORMAT, buffer, 0)
        if magic != ZeroCopyPacketParser.MAGIC_BYTE:
            raise ValueError(f"Invalid packet magic byte: {hex(magic)}")
        
        if length > ZeroCopyPacketParser.MAX_PAYLOAD_LENGTH:
            raise ValueError(f"Payload length {length} exceeds maximum allowed size ({ZeroCopyPacketParser.MAX_PAYLOAD_LENGTH})")
        
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
        if length > ZeroCopyPacketParser.MAX_PAYLOAD_LENGTH:
            raise ValueError("Payload length exceeds maximum allowed size")
        header = struct.pack(ZeroCopyPacketParser.HEADER_FORMAT, ZeroCopyPacketParser.MAGIC_BYTE, length)
        return header + payload_bytes
=======
from typing import Tuple, Dict, Any, Optional

class ZeroCopyPacketParser:
    """Zero-allocation packet parser utilizing memoryviews and struct unpacking."""
    
    HEADER_FORMAT = "!IB36sI"  # Magic (4B), Type (1B), UUID/ID (36B), Payload Length (4B)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    @staticmethod
    def parse_header(buffer: memoryview) -> Tuple[int, int, str, int, memoryview]:
        """Parses packet header from memoryview without byte string allocation."""
        if len(buffer) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError(f"Buffer too small for header: {len(buffer)} < {ZeroCopyPacketParser.HEADER_SIZE}")
        
        header_view = buffer[:ZeroCopyPacketParser.HEADER_SIZE]
        magic, msg_type, raw_id, payload_len = struct.unpack(ZeroCopyPacketParser.HEADER_FORMAT, header_view)
        
        msg_id = raw_id.rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_view = buffer[ZeroCopyPacketParser.HEADER_SIZE : ZeroCopyPacketParser.HEADER_SIZE + payload_len]
        return magic, msg_type, msg_id, payload_len, payload_view

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        """Serializes message header and payload into wire format."""
        padded_id = msg_id.encode('utf-8').ljust(36, b'\x00')[:36]
        payload_len = len(payload)
        header = struct.pack(ZeroCopyPacketParser.HEADER_FORMAT, magic, msg_type, padded_id, payload_len)
        return header + payload
>>>>>>> origin/main
