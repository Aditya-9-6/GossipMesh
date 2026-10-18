import struct
from typing import Tuple, Optional

class ZeroCopyPacketParser:
    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        padded_id = msg_id.encode('utf-8').ljust(32, b'\x00')[:32]
        header = struct.pack(">I I 32s I", magic, msg_type, padded_id, len(payload))
        return header + payload

    @staticmethod
    def parse_header_raw(buf: memoryview) -> Tuple[int, int, str, int]:
        magic, msg_type, raw_id, payload_len = struct.unpack_from(">I I 32s I", buf, 0)
        msg_id = raw_id.rstrip(b'\x00').decode('utf-8', errors='ignore')
        return magic, msg_type, msg_id, payload_len

    @staticmethod
    def parse_header(buf: memoryview) -> Tuple[int, int, str, int, memoryview]:
        magic, msg_type, msg_id, payload_len = ZeroCopyPacketParser.parse_header_raw(buf)
        header_len = 4 + 4 + 32 + 4
        payload_view = buf[header_len:header_len + payload_len]
        return magic, msg_type, msg_id, payload_len, payload_view
