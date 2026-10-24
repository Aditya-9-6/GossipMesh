import logging
from typing import Dict, List, Any, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy

logger = logging.getLogger(__name__)


class P2PSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy()
        self.entropy_tracker = VectorClockEntropy()

    def sync_state(self, peer_state: Any) -> bool:
        logger.info(f"Syncing state with peer {peer_state}")
        if isinstance(peer_state, dict):
            self.entropy_tracker.update(peer_state)
        return True

    def sync(self, peer_data: Any) -> None:
        self.sync_state(peer_data)


class Syncer(P2PSyncer):
    pass
