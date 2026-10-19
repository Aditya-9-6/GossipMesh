from typing import Dict, List, Tuple, Optional


class VectorClockEntropy:
    """Evaluates vector clock entropy for sync peer selection."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size

    def select_best_peers(
        self, local_clock: Dict[str, int], active_peers: Dict[str, Dict[str, int]], top_k: int = 3
    ) -> List[Tuple[str, float]]:
        scored = []
        for peer_id, p_clock in active_peers.items():
            diff = sum(
                abs(p_clock.get(k, 0) - local_clock.get(k, 0)) for k in set(local_clock.keys()).union(p_clock.keys())
            )
            scored.append((peer_id, float(diff)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


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
