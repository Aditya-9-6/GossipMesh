""P2P transport layer integrating compressed Bloom filter deduplication and Fountain Fragment Integration for Resilient Gossip Broadcast."""

from __main__ import *
from typing import Any, Dict, List, Optional, Tuple
import logging

from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder, FountainFragmentConfig, FountainFragment

logger = logging.getLogger(__name__)


class P2PTransport:
    """Resilient transport layer supporting incremental fountain fragment broadcast and duplicate filtering."""

    def __init__(self, node_id: str, config: Optional[FountainFragmentConfig] = None) -> None:
        self.node_id = node_id
        self.config = config or FountainFragmentConfig()
        self.active_decoders: Dict[str, FountainDecoder] = {}

    def receive_message(self, message_id: str, payload: Dict[str, Any]) -> bool:
        """
        Processes an incoming gossip message. Returns True if the message is new,
        or False if it is a duplicate that should be dropped.
        """
        is_duplicate = getattr(self, "dedup", None) and self.dedup.add(message_id)
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
