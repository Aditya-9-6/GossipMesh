"""P2P transport layer integrating compressed Bloom filter deduplication for gossip messages.
"""

import logging
from typing import Optional, Dict, Any
from gossipmesh.p2p.dedup import CompressedBloomFilterDedup

logger = logging.getLogger(__name__)


class GossipTransport:
    """
    Transport layer handling gossip message dissemination with deduplication protection.
    """

    def __init__(self, node_id: str, dedup_filter: Optional[CompressedBloomFilterDedup] = None) -> None:
        self.node_id = node_id
        self.dedup = dedup_filter or CompressedBloomFilterDedup()

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
