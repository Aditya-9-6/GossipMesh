import struct
from typing import Tuple

class ZeroCopyPacketParser:
    HEADER_SIZE = 45

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        msg_id_bytes = msg_id.encode('utf-8').ljust(32, b'\x00')[:32]
        payload_len = len(payload)
        header = struct.pack(">I B 32s I", magic, msg_type, msg_id_bytes, payload_len)
        return header + payload

    @staticmethod
    def parse_header(buffer: memoryview) -> Tuple[int, int, str, int, memoryview]:
        if len(buffer) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError(f"Buffer too small for header: {len(buffer)} < {ZeroCopyPacketParser.HEADER_SIZE}")
        header_bytes = bytes(buffer[:ZeroCopyPacketParser.HEADER_SIZE])
        magic, msg_type, msg_id_bytes, payload_len = struct.unpack(">I B 32s I", header_bytes[:41])
        msg_id = msg_id_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_view = buffer[ZeroCopyPacketParser.HEADER_SIZE:ZeroCopyPacketParser.HEADER_SIZE + payload_len]
        return magic, msg_type, msg_id, payload_len, payload_view
