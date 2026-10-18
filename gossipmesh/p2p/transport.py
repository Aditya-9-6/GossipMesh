import asyncio
import logging
from typing import List, Optional
from gossipmesh.p2p.fragmentation import MessageFragmenter, MessageReassembler, PacketFragment

logger = logging.getLogger(__name__)


class P2PTransport:
    def __init__(self, mtu: int = 1024, timeout: float = 30.0):
        self.mtu = mtu
        self.reassembler = MessageReassembler(timeout_seconds=timeout)

    def prepare_outgoing(self, data: bytes) -> List[dict]:
        fragments = MessageFragmenter.fragment(data, chunk_size=self.mtu)
        return [f.to_dict() for f in fragments]

    def handle_incoming_fragment(self, fragment_dict: dict) -> Optional[bytes]:
        try:
            fragment = PacketFragment.from_dict(fragment_dict)
            return self.reassembler.add_fragment(fragment)
        except Exception as e:
            logger.error(f"Failed to process incoming fragment: {e}")
            raise
