from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PacketFragment:
    message_id: str
    fragment_index: int
    total_fragments: int
    payload: bytes
    checksum: str


class MessageFragmentationManager:
    """
    Handles packet fragmentation for large gossip payloads and reassembly with timeout buffers.
    """

    def __init__(self, timeout_sec: float = 30.0):
        self.timeout_sec = timeout_sec
        self.buffers: Dict[str, Dict[str, Any]] = {}

    def add_fragment(self, frag: PacketFragment) -> Optional[bytes]:
        """
        Adds a fragment. Returns reassembled payload if all fragments have arrived, otherwise None.
        """
        now = time.time()
        self._cleanup_expired(now)

        if frag.message_id not in self.buffers:
            self.buffers[frag.message_id] = {
                "total": frag.total_fragments,
                "fragments": {},
                "expires_at": now + self.timeout_sec,
            }

        buf = self.buffers[frag.message_id]
        buf["fragments"][frag.fragment_index] = frag.payload

        if len(buf["fragments"]) == buf["total"]:
            # Reassemble in order
            ordered_parts = [buf["fragments"][i] for i in range(buf["total"])]
            assembled = b"".join(ordered_parts)
            del self.buffers[frag.message_id]
            return assembled

        return None

    def _cleanup_expired(self, now: float) -> None:
        expired = [msg_id for msg_id, data in self.buffers.items() if data["expires_at"] < now]
        for msg_id in expired:
            del self.buffers[msg_id]


def fragment_message(
    payload: bytes, message_id: Optional[str] = None, max_fragment_size: int = 1024
) -> List[PacketFragment]:
    """
    Splits a large payload into a sequence of PacketFragments.
    """
    msg_id = message_id or str(uuid.uuid4())
    if not payload:
        return [PacketFragment(message_id=msg_id, fragment_index=0, total_fragments=1, payload=b"", checksum="0")]

    fragments = []
    total_frags = (len(payload) + max_fragment_size - 1) // max_fragment_size

    for i in range(total_frags):
        start = i * max_fragment_size
        chunk = payload[start : start + max_fragment_size]
        fragments.append(
            PacketFragment(
                message_id=msg_id,
                fragment_index=i,
                total_fragments=total_frags,
                payload=chunk,
                checksum=str(hash(chunk)),
            )
        )

    return fragments
