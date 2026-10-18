import struct
from typing import Tuple, Optional, Union, BinaryIO
import asyncio

class ZeroCopyPacketParser:
    HEADER_FORMAT = "!I H 32s I"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        msg_id_bytes = msg_id.encode('utf-8')[:32].ljust(32, b'\x00')
        header = struct.pack(ZeroCopyPacketParser.HEADER_FORMAT, magic, msg_type, msg_id_bytes, len(payload))
        return header + payload

    @staticmethod
    def parse_header(header_bytes: bytes) -> Tuple[int, int, str, int]:
        if len(header_bytes) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError("Insufficient bytes for header")
        magic, msg_type, msg_id_bytes, payload_len = struct.unpack(
            ZeroCopyPacketParser.HEADER_FORMAT, header_bytes[:ZeroCopyPacketParser.HEADER_SIZE]
        )
        msg_id = msg_id_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
        return magic, msg_type, msg_id, payload_len

class TransportSocketReader:
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553):
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        header_data = await self.reader.readexactly(ZeroCopyPacketParser.HEADER_SIZE)
        if not header_data or len(header_data) < ZeroCopyPacketParser.HEADER_SIZE:
            return None
        magic, msg_type, msg_id, payload_len = ZeroCopyPacketParser.parse_header(header_data)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid magic number: {hex(magic)}, expected {hex(self.expected_magic)}")
        payload_data = await self.reader.readexactly(payload_len)
        return msg_type, msg_id, memoryview(payload_data)
