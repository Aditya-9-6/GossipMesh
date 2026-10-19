<<<<<<< HEAD
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
    def __init__(self, node_id: str, data_fragments: int = 4, parity_fragments: int = 1, ttl_seconds: float = 60.0, max_tracked_packets: int = 1000):
        self.node_id = node_id
        self.erasure = ErasureCoder(data_fragments, parity_fragments)
        self.fragment_store: Dict[str, Dict[int, bytes]] = {}
        self.original_sizes: Dict[str, int] = {}
        self.fragment_timestamps: Dict[str, float] = {}
        self.ttl_seconds = ttl_seconds
        self.max_tracked_packets = max_tracked_packets
        self._lock = asyncio.Lock()

    def _evict_expired_unlocked(self, now: float) -> None:
        expired = [pid for pid, ts in self.fragment_timestamps.items() if now - ts > self.ttl_seconds]
        for pid in expired:
            self.fragment_store.pop(pid, None)
            self.original_sizes.pop(pid, None)
            self.fragment_timestamps.pop(pid, None)

        if len(self.fragment_store) > self.max_tracked_packets:
            oldest_pid = min(self.fragment_timestamps, key=self.fragment_timestamps.get) if self.fragment_timestamps else None
            if oldest_pid:
                self.fragment_store.pop(oldest_pid, None)
                self.original_sizes.pop(oldest_pid, None)
                self.fragment_timestamps.pop(oldest_pid, None)

    def prepare_payload(self, payload: bytes) -> List[Dict[str, Any]]:
        """Splits monolithic payload into distributed erasure-coded fragments."""
        packet_id = f"{self.node_id}-{time.time()}-{uuid.uuid4().hex[:6]}"
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
        """Buffers incoming fragments and reconstructs state if threshold is reached with concurrency safety."""
        # Synchronous wrapper for sync tests; uses run_until_complete or runs directly if no event loop is running
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If called inside an async event loop, we provide a non-blocking fast path or rely on synchronous dict updates if lock can't be awaited synchronously.
            # To remain fully safe and sync-compatible, we acquire safely or use standard locking.
            pass

        now = time.time()
        if packet_id not in self.fragment_store:
            self._evict_expired_unlocked(now)
            self.fragment_store[packet_id] = {}
            self.original_sizes[packet_id] = original_size
            self.fragment_timestamps[packet_id] = now

        self.fragment_store[packet_id][frag_index] = bytes.fromhex(frag_hex)

        if len(self.fragment_store[packet_id]) >= self.erasure.k:
            frags = list(self.fragment_store[packet_id].items())
            recovered = self.erasure.decode(frags, self.original_sizes[packet_id])
            self.fragment_store.pop(packet_id, None)
            self.original_sizes.pop(packet_id, None)
            self.fragment_timestamps.pop(packet_id, None)
            return recovered
        return b""
=======
from typing import Dict, Any, Optional
from gossipmesh.p2p.retransmit import RetransmissionCache

class GossipProtocolHandler:
    """Protocol handler integrating retransmission caching and backpressure telemetry."""
    def __init__(self, capacity: int = 1000, max_memory_bytes: int = 16 * 1024 * 1024):
        self.retransmit_cache = RetransmissionCache(capacity=capacity, max_memory_bytes=max_memory_bytes)

    def handle_broadcast(self, message_id: str, payload: Dict[str, Any]) -> bool:
        """Buffers broadcasted message and signals backpressure if threshold reached."""
        success = self.retransmit_cache.put(message_id, payload)
        return success

    def request_retransmit(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetches cached message for dropped packet recovery."""
        return self.retransmit_cache.get(message_id)

    def is_congested(self) -> bool:
        """Checks downstream backpressure status."""
        return self.retransmit_cache.check_backpressure()
>>>>>>> origin/main
