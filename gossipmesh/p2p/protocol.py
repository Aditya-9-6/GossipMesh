import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional
from gossipmesh.p2p.erasure import ErasureCoder

logger = logging.getLogger("gossipmesh.p2p.protocol")

class EntropyControlFrame:
    def __init__(self, sender_id: str, vector_clock: Dict[str, int], merkle_digest: str, message_id: Optional[str] = None, timestamp: Optional[float] = None):
        self.sender_id = sender_id
        self.vector_clock = vector_clock
        self.merkle_digest = merkle_digest
        self.message_id = message_id or str(uuid.uuid4())
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "vector_clock": self.vector_clock,
            "merkle_digest": self.merkle_digest,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntropyControlFrame':
        return cls(
            sender_id=data["sender_id"],
            vector_clock=data["vector_clock"],
            merkle_digest=data["merkle_digest"],
            message_id=data.get("message_id"),
            timestamp=data.get("timestamp"),
        )

class GossipProtocol:
    def __init__(self, node_id: str, data_fragments: int = 4, parity_fragments: int = 2):
        self.node_id = node_id
        self.erasure = ErasureCoder(data_fragments, parity_fragments)
        self.fragment_store: Dict[str, Dict[int, bytes]] = {}
        self.original_sizes: Dict[str, int] = {}

    def prepare_payload(self, payload: bytes) -> List[Dict[str, Any]]:
        """Splits monolithic payload into distributed erasure-coded fragments."""
        packet_id = f"{self.node_id}-{asyncio.get_event_loop().time()}"
        frags = self.erasure.encode(payload)
        self.original_sizes[packet_id] = len(payload)
        return [
            {
                "packet_id": packet_id,
                "frag_index": idx,
                "data": frag.hex(),
                "original_size": len(payload)
            }
            for idx, frag in frags
        ]

    def receive_fragment(self, packet_id: str, frag_index: int, frag_hex: str, original_size: int) -> bytes:
        """Buffers incoming fragments and reconstructs state if threshold is reached."""
        if packet_id not in self.fragment_store:
            self.fragment_store[packet_id] = {}
            self.original_sizes[packet_id] = original_size

        self.fragment_store[packet_id][frag_index] = bytes.fromhex(frag_hex)

        if len(self.fragment_store[packet_id]) >= self.erasure.k:
            frags = list(self.fragment_store[packet_id].items())
            recovered = self.erasure.decode(frags, self.original_sizes[packet_id])
            del self.fragment_store[packet_id]
            del self.original_sizes[packet_id]
            return recovered
        return b""
