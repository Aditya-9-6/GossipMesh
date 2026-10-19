import logging
from typing import Any, Dict, Optional
from gossipmesh.p2p.entropy import EntropyEvaluator

logger = logging.getLogger(__name__)


class PeerSyncer:
    """Handles peer synchronization and entropy evaluation."""

    def __init__(self, evaluator: Optional[EntropyEvaluator] = None) -> None:
        self.evaluator = evaluator or EntropyEvaluator()

    def sync_peer(self, peer_data: Dict[str, Any]) -> bool:
        """Evaluates peer entropy and performs synchronization."""
        score = self.evaluator.evaluate(peer_data)
        return score >= 0.0
