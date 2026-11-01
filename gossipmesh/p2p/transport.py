"""P2P transport layer integrating compressed Bloom filter deduplication for gossip messages."""

import logging
from typing import Optional, Dict, Any
from gossipmesh.p2p.dedup import CompressedBloomFilterDedup
from gossipmesh.p2p.fragmentation import PacketFragmenter, PacketReassembler

logger = logging.getLogger(__name__)


class P2PTransport:
    """
    Transport layer handling gossip message dissemination and packet fragmentation.
    """

    def __init__(self, mtu: int = 1400, dedup_filter: Optional[CompressedBloomFilterDedup] = None) -> None:
        self.mtu = mtu
        self.dedup = dedup_filter or CompressedBloomFilterDedup()
        self.fragmenter = PacketFragmenter(mtu=mtu)
        self.reassembler = PacketReassembler()

    def send_gossip_sync(self, peer_id: str, payload: bytes) -> bool:
        """Fragments and sends gossip sync payload synchronously."""
        fragments = self.fragmenter.fragment("gossip-sync", payload)
        return len(fragments) > 0


class GossipTransport(P2PTransport):
    """Legacy compatibility wrapper."""

    def __init__(self, node_id: str, dedup_filter: Optional[CompressedBloomFilterDedup] = None) -> None:
        super().__init__(dedup_filter=dedup_filter)
        self.node_id = node_id

    def receive_message(self, message_id: str, payload: Dict[str, Any]) -> bool:
        is_duplicate = self.dedup.add(message_id)
        if is_duplicate:
            logger.debug(f"Node {self.node_id} dropped duplicate gossip message: {message_id}")
            return False
        logger.debug(f"Node {self.node_id} accepted new gossip message: {message_id}")
        return True
