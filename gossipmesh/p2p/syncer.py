import asyncio
import logging
from typing import Dict, Set, Optional, Any
from gossipmesh.p2p.entropy import VectorClockEntropy

logger = logging.getLogger(__name__)


class StateSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    async def sync_state(self, peer_id: str, remote_clock: Dict[str, int]) -> None:
        logger.info(f"Syncing state with peer {peer_id}")
        self.entropy.merge(remote_clock)
