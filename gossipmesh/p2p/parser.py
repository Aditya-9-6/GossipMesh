import struct
import uuid
from typing import Tuple


class ZeroCopyPacketParser:
    HEADER_SIZE = 4 + 4 + 16 + 4  # magic (4) + msg_type (4) + msg_id (16 bytes UUID) + payload_len (4)

    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        try:
            uuid_bytes = uuid.UUID(msg_id).bytes
        except Exception:
            uuid_bytes = uuid.uuid5(uuid.NAMESPACE_DNS, msg_id).bytes
            
        payload_len = len(payload)
        return struct.pack(">II16sI", magic, msg_type, uuid_bytes, payload_len) + payload

    @staticmethod
    def deserialize_header(header_bytes: bytes) -> Tuple[int, int, str, int]:
        magic, msg_type, uuid_bytes, payload_len = struct.unpack(">II16sI", header_bytes)
        msg_id = str(uuid.UUID(bytes=uuid_bytes))
        return magic, msg_type, msg_id, payload_len
