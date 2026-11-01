"""P2P transport layer integrating compressed Bloom filter deduplication for gossip messages."""

import logging
from typing import Optional, Dict, Any
from gossipmesh.p2p.dedup import CompressedBloomFilterDedup
from gossipmesh.p2p.fragmentation import PacketFragmenter, PacketReassembler

logger = logging.getLogger(__name__)


class P2PTransport:
    """
    Transport layer handling P2P messaging, fragmentation, and gossip dissemination with deduplication protection.
    """

    def __init__(
        self, node_id: str = "node-local", mtu: int = 1024, dedup_filter: Optional[CompressedBloomFilterDedup] = None
    ) -> None:
        self.node_id = node_id
        self.mtu = mtu
        self.dedup = dedup_filter or CompressedBloomFilterDedup()
        self.fragmenter = PacketFragmenter(mtu=mtu)
        self.reassembler = PacketReassembler()

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

    def send_gossip_sync(self, peer_id: str, payload: bytes) -> bool:
        """Synchronously sends gossip payload, fragmenting if necessary."""
        fragments = self.fragmenter.fragment("msg-sync", payload)
        return len(fragments) > 0


GossipTransport = P2PTransport
