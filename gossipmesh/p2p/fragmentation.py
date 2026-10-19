import zlib
import time
import uuid
from typing import Dict, List, Optional, Any

DEFAULT_CHUNK_SIZE = 1024
DEFAULT_TIMEOUT_SECONDS = 30.0


class PacketFragment:
    def __init__(self, message_id: str, index: int, total: int, payload: bytes, checksum: int):
        self.message_id = message_id
        self.index = index
        self.total = total
        self.payload = payload
        self.checksum = checksum

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "index": self.index,
            "total": self.total,
            "payload": self.payload.hex(),
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PacketFragment":
        return cls(
            message_id=data["message_id"],
            index=data["index"],
            total=data["total"],
            payload=bytes.fromhex(data["payload"]),
            checksum=data["checksum"],
        )


class MessageFragmenter:
    @staticmethod
    def fragment(data: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[PacketFragment]:
        if not data:
            checksum = zlib.crc32(b"")
            return [PacketFragment(str(uuid.uuid4()), 0, 1, b"", checksum)]

        checksum = zlib.crc32(data)
        message_id = str(uuid.uuid4())
        total = (len(data) + chunk_size - 1) // chunk_size
        fragments = []

        for i in range(total):
            start = i * chunk_size
            end = min(start + chunk_size, len(data))
            chunk = data[start:end]
            fragments.append(
                PacketFragment(
                    message_id=message_id,
                    index=i,
                    total=total,
                    payload=chunk,
                    checksum=checksum,
                )
            )
        return fragments


class MessageReassembler:
    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds
        self.buffers: Dict[str, Dict[str, Any]] = {}

    def _evict_expired(self, now: float):
        expired_keys = [
            msg_id for msg_id, state in self.buffers.items() if now - state["last_update"] > self.timeout_seconds
        ]
        for msg_id in expired_keys:
            del self.buffers[msg_id]

    def add_fragment(self, fragment: PacketFragment) -> Optional[bytes]:
        now = time.time()
        self._evict_expired(now)

        msg_id = fragment.message_id
        if msg_id not in self.buffers:
            self.buffers[msg_id] = {
                "total": fragment.total,
                "checksum": fragment.checksum,
                "fragments": {},
                "last_update": now,
            }

        state = self.buffers[msg_id]
        state["last_update"] = now
        state["fragments"][fragment.index] = fragment.payload

        if len(state["fragments"]) == state["total"]:
            ordered_chunks = [state["fragments"][i] for i in range(state["total"])]
            full_data = b"".join(ordered_chunks)
            computed_crc = zlib.crc32(full_data)
            del self.buffers[msg_id]

            if computed_crc != state["checksum"]:
                raise ValueError("CRC32 checksum mismatch during packet reassembly")
            return full_data

        return None
