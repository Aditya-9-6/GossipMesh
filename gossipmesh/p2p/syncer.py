import asyncio
import logging
from typing import Dict, Set, Any

from gossipmesh.p2p.entropy import VectorClockEntropy

logger = logging.getLogger(__name__)


class P2PSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    async def sync_loop(self) -> None:
        while True:
            await asyncio.sleep(5)
            logger.debug("Running P2P sync loop...")
