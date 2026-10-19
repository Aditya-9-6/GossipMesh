import struct
import asyncio
import logging
from typing import Any, Optional, Tuple, AsyncIterator

logger = logging.getLogger(__name__)

class ZeroCopyPacketParser:
    """Zero-copy packet parser for high-performance Gossip transport frames."""
    
    HEADER_FORMAT = "!IBH"  # Magic (4B), Version/Flags (1B), Payload Length (2B)
    HEADER_SIZE = struct.calc0size(HEADER_FORMAT) if hasattr(struct, 'calc0size') else struct.calcsize(HEADER_FORMAT)

    @staticmethod
    def parse_header(buffer: bytes) -> Tuple[int, int, int]:
        if len(buffer) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError("Buffer too small for packet header")
        magic, flags, length = struct.unpack(ZeroCopyPacketParser.HEADER_FORMAT, buffer[:ZeroCopyPacketParser.HEADER_SIZE])
        return magic, flags, length

class TransportSocketReader:
    def __init__(self, reader: Any, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> bytes:
        header_data = await self.reader.readexactly(ZeroCopyPacketParser.HEADER_SIZE)
        magic, flags, length = ZeroCopyPacketParser.parse_header(header_data)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid magic number: {hex(magic)}")
        payload = await self.reader.readexactly(length)
        return payload
