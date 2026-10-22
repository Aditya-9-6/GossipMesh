from typing import Dict, List, Tuple, Optional
from gossipmesh.p2p.entropy import VectorClockEntropy


class AntiEntropySyncer:
    """Anti-entropy synchronization daemon coordinating peer sessions using entropy-driven selection."""

    def __init__(self, node_id: str, window_size: int = 100):
        self.node_id = node_id
        self.entropy_evaluator = VectorClockEntropy(window_size=window_size)

    def select_sync_peers(
        self, local_clock: Dict[str, int], active_peers: Dict[str, Dict[str, int]], limit: int = 3
    ) -> List[Tuple[str, float]]:
        """Selects the best peers to synchronize with based on vector clock entropy."""
        return self.entropy_evaluator.select_best_peers(local_clock, active_peers, top_k=limit)
