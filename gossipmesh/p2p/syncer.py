import logging
from typing import Any, Optional

from gossipmesh.p2p.entropy import VectorClockEntropy

logger = logging.getLogger(__name__)


class P2PSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()

    def sync_state(self, peer_state: Any) -> None:
        logger.info(f"Syncing state with peer {peer_state}")
