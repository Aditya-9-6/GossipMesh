import struct
from typing import Tuple, Optional

class ZeroCopyPacketParser:
    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        msg_id_bytes = msg_id.encode('utf-8').ljust(32, b'\x00')[:32]
        length = len(payload)
        header = struct.pack('!I B 32s I', magic, msg_type, msg_id_bytes, length)
        return header + payload

    @staticmethod
    def parse_header(buf: memoryview) -> Tuple[int, int, str, int]:
        # 4 (magic) + 1 (type) + 32 (id) + 4 (length) = 41 bytes
        header_bytes = bytes(buf[:41])
        magic, msg_type, msg_id_bytes, length = struct.unpack('!I B 32s I', header_bytes)
        msg_id = msg_id_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
        return magic, msg_type, msg_id, length

class TransportSocketReader:
    def __init__(self, reader: Any, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, bytes]]:
        header_data = await self.reader.readexactly(41)
        if not header_data or len(header_data) < 41:
            return None
        buf = memoryview(header_data)
        magic, msg_type, msg_id, length = ZeroCopyPacketParser.parse_header(buf)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid magic number: {hex(magic)}")
        payload = await self.reader.readexactly(length)
        return msg_type, msg_id, bytes(payload)
