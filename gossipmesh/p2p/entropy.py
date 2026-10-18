import math
from typing import Dict, List, Tuple
from collections import deque

class VectorClockEntropy:
    """Calculates state divergence entropy between local and peer vector clocks."""
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.history: deque = deque(maxlen=window_size)

    def calculate_divergence(self, local_clock: Dict[str, int], peer_clock: Dict[str, int]) -> float:
        """Calculates normalized Shannon divergence/distance score between two vector clocks."""
        all_keys = set(local_clock.keys()).union(set(peer_clock.keys()))
        if not all_keys:
            return 0.0

        diff_squares = 0.0
        for k in all_keys:
            v_local = local_clock.get(k, 0)
            v_peer = peer_clock.get(k, 0)
            diff_squares += (v_local - v_peer) ** 2

        distance = math.sqrt(diff_squares)
        entropy_score = 1.0 - (1.0 / (1.0 + distance))
        self.history.append((local_clock, peer_clock, entropy_score))
        return float(entropy_score)

    def select_best_peers(self, local_clock: Dict[str, int], peer_clocks: Dict[str, Dict[str, int]], top_k: int = 3) -> List[Tuple[str, float]]:
        """Ranks and selects top peers with highest divergence score for anti-entropy sessions."""
        scores = []
        for peer_id, p_clock in peer_clocks.items():
            score = self.calculate_divergence(local_clock, p_clock)
            scores.append((peer_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class AntiEntropyEngine:
    """Anti-entropy engine managing state store and divergence reconciliation."""
    def __init__(self, node_id: str, window_size: int = 100):
        self.node_id = node_id
        self.state_store: Dict[str, Any] = {}
        self.entropy_evaluator = VectorClockEntropy(window_size=window_size)

    def set_state(self, key: str, value: Any) -> None:
        """Sets key-value state in the local store."""
        self.state_store[key] = value

    def reconcile_divergence(self, peer_state: Dict[str, Any]) -> List[str]:
        """Finds differences between local state store and peer state store."""
        diffs = []
        all_keys = set(self.state_store.keys()).union(set(peer_state.keys()))
        for k in all_keys:
            if self.state_store.get(k) != peer_state.get(k):
                diffs.append(k)
        return diffs
