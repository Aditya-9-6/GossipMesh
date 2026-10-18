import struct
import asyncio
from typing import Tuple, Optional

class ZeroCopyPacketParser:
    """Parses packets efficiently without unnecessary memory allocations."""
    
    HEADER_FORMAT = "!I I 32s I"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        encoded_id = msg_id.encode('utf-8')[:32].ljust(32, b'\x00')
        header = struct.pack(ZeroCopyPacketParser.HEADER_FORMAT, magic, msg_type, encoded_id, len(payload))
        return header + payload


class TransportSocketReader:
    """Reads network packets from an asyncio stream reader with validation."""
    
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        header_data = await self.reader.readexactly(ZeroCopyPacketParser.HEADER_SIZE)
        if not header_data or len(header_data) < ZeroCopyPacketParser.HEADER_SIZE:
            return None
        
        magic, msg_type, raw_id, payload_len = struct.unpack(ZeroCopyPacketParser.HEADER_FORMAT, header_data)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid packet magic: 0x{magic:08X} expected 0x{self.expected_magic:08X}")
        
        msg_id = raw_id.rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_bytes = await self.reader.readexactly(payload_len)
        return msg_type, msg_id, memoryview(payload_bytes)
