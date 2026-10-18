import struct
from typing import Tuple

class ZeroCopyPacketParser:
    HEADER_SIZE = 4 + 4 + 32 + 4  # magic (4) + msg_type (4) + msg_id (32 bytes string padded/encoded) + payload_len (4)

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        encoded_id = msg_id.encode('utf-8').ljust(32, b'\x00')[:32]
        payload_len = len(payload)
        header = struct.pack(">II32sI", magic, msg_type, encoded_id, payload_len)
        return header + payload

    @staticmethod
    def parse_header(header_bytes: memoryview) -> Tuple[int, int, str, int, memoryview]:
        if len(header_bytes) < ZeroCopyPacketParser.HEADER_SIZE:
            raise ValueError("Insufficient bytes for header")
        
        raw_header = header_bytes[:ZeroCopyPacketParser.HEADER_SIZE]
        magic, msg_type, encoded_id, payload_len = struct.unpack(">II32sI", bytes(raw_header))
        msg_id = encoded_id.rstrip(b'\x00').decode('utf-8', errors='ignore')
        payload_view = header_bytes[ZeroCopyPacketParser.HEADER_SIZE : ZeroCopyPacketParser.HEADER_SIZE + payload_len]
        return magic, msg_type, msg_id, payload_len, payload_view
