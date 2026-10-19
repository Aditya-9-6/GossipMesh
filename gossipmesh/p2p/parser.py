import struct
from typing import Tuple, Dict, Any, Optional

class ZeroCopyPacketParser:
    """Zero-copy parser for gossip wire packets using memoryview and struct unpacking."""
    
    HEADER_FORMAT = "!IB36sI"  # Magic (4B), Type (1B), UUID/ID (36B), Payload Length (4B)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAGIC_BYTE = 0x47475350  # 4-byte magic for extended header, or standard integer
    MAX_PAYLOAD_LENGTH = 16 * 1024 * 1024  # 16 MB max safety limit

    @staticmethod
    def parse_header(buffer: memoryview) -> Tuple[int, int, str, int, memoryview]:
        """Parses packet header and returns payload view without allocating new byte strings."""
        if len(buffer) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError(f"Buffer too small for header: {len(buffer)} < {ZeroCopyPacketParser.HEADER_SIZE}")
        
        header_view = buffer[:ZeroCopyPacketParser.HEADER_SIZE]
        magic, msg_type, raw_id, payload_len = struct.unpack(ZeroCopyPacketParser.HEADER_FORMAT, header_view)
        
        if payload_len > ZeroCopyPacketParser.MAX_PAYLOAD_LENGTH:
            raise ValueError(f"Payload length {payload_len} exceeds maximum allowed size ({ZeroCopyPacketParser.MAX_PAYLOAD_LENGTH})")
        
        msg_id = raw_id.rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_view = buffer[ZeroCopyPacketParser.HEADER_SIZE : ZeroCopyPacketParser.HEADER_SIZE + payload_len]
        return magic, msg_type, msg_id, payload_len, payload_view

    @staticmethod
    def extract_payload(buffer: memoryview, length: int) -> memoryview:
        """Extracts payload zero-copy using memoryview slicing."""
        total_needed = ZeroCopyPacketParser.HEADER_SIZE + length
        if len(buffer) < total_needed:
            raise ValueError("Incomplete packet buffer")
        
        return buffer[ZeroCopyPacketParser.HEADER_SIZE:total_needed]

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        """Serializes message header and payload into wire format."""
        payload_len = len(payload)
        if payload_len > ZeroCopyPacketParser.MAX_PAYLOAD_LENGTH:
            raise ValueError("Payload length exceeds maximum allowed size")
        padded_id = msg_id.encode('utf-8').ljust(36, b'\x00')[:36]
        header = struct.pack(ZeroCopyPacketParser.HEADER_FORMAT, magic, msg_type, padded_id, payload_len)
        return header + payload

    @staticmethod
    def serialize_packet(magic: int, msg_type: int, msg_id: str, payload_bytes: bytes) -> bytes:
        """Helper to construct valid wire format packets for testing/transport."""
        return ZeroCopyPacketParser.serialize_header(magic, msg_type, msg_id, payload_bytes)
