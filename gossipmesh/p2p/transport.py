"""
P2P Network Transport with Fountain Fragment Integration and Resilient Gossip Broadcast.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging

from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder, FountainFragmentConfig, FountainFragment
from gossipmesh.p2p.scoring import PeerScoreTracker
from gossipmesh.utils.dedup import BloomFilterDedup

logger = logging.getLogger(__name__)


class LeakyBucketStreamLimiter:
    """Simple leaky bucket rate limiter for stream control."""
    def __init__(self, capacity: int, rate: float) -> None:
        self.capacity = capacity
        self.rate = rate
        self.level = 0.0

    def consume(self, amount: float = 1.0) -> bool:
        if self.level + amount <= self.capacity:
            self.level += amount
            return True
        return False


class PacketFragmenter:
    """Utility for fragmenting and reassembling network packets."""
    def __init__(self, max_size: int = 1024) -> None:
        self.max_size = max_size

    def fragment(self, payload: bytes) -> List[bytes]:
        return [payload[i:i + self.max_size] for i in range(0, len(payload), self.max_size)]


class P2PTransport:
    """Resilient transport layer supporting incremental fountain fragment broadcast, scoring, and deduplication."""

    def __init__(self, node_id: str, config: Optional[FountainFragmentConfig] = None) -> None:
        self.node_id = node_id
        self.config = config or FountainFragmentConfig()
        self.active_decoders: Dict[str, FountainDecoder] = {}
        self.dedup = BloomFilterDedup()
        self.score_tracker = PeerScoreTracker()
        self.stream_limiter = LeakyBucketStreamLimiter(capacity=100, rate=10.0)
        self.fragmenter = PacketFragmenter()
        self._running = False

    async def start(self) -> None:
        """Starts the P2P transport layer."""
        self._running = True
        logger.info(f"P2PTransport started for node {self.node_id}")

    async def stop(self) -> None:
        """Stops the P2P transport layer."""
        self._running = False
        logger.info(f"P2PTransport stopped for node {self.node_id}")

    def receive_message(self, message_id: str, payload: Dict[str, Any]) -> bool:
        """
        Processes an incoming gossip message. Returns True if the message is new,
        or False if it is a duplicate that should be dropped.
        """
        is_duplicate = self.dedup.add(message_id)
        if is_duplicate:
            logger.debug(f"Node {self.node_id} dropped duplicate gossip message: {message_id}")
            return False

        logger.debug(f"Node {self.node_id} accepted new gossip message: {message_id}")
        return True

    def prepare_broadcast(self, payload: bytes, session_id: str, count: int) -> List[bytes]:
        encoder = FountainEncoder(payload, self.config)
        fragments = []
        for i in range(count):
            frag = encoder.generate_symbol(i, session_id)
            fragments.append(frag.serialize())
        return fragments

    def receive_fragment(self, raw_fragment: bytes, original_len: Optional[int] = None) -> Tuple[bool, Optional[bytes]]:
        frag = FountainFragment.deserialize(raw_fragment)
        if frag.session_id not in self.active_decoders:
            self.active_decoders[frag.session_id] = FountainDecoder(frag.total_chunks, self.config.chunk_size)
        
        decoder = self.active_decoders[frag.session_id]
        is_complete = decoder.add_fragment(frag)
        if is_complete:
            data = decoder.get_reassembled_data(original_len)
            return True, data
        return False, None
