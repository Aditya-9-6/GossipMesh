import math
import time
import threading
from collections import deque
from typing import Dict, List, Optional, Tuple, Any

class EntropyChurnDefense:
    """Calculates sliding-window entropy over incoming peer message metadata
    to detect and penalize Sybil nodes flooding fake heartbeat vectors.
    """
    def __init__(self, window_size: int = 50, entropy_threshold: float = 1.2, max_ticks_to_drop: int = 3):
        self.window_size = window_size
        self.entropy_threshold = entropy_threshold
        self.max_ticks_to_drop = max_ticks_to_drop
        # node_id -> deque of metadata feature values or timestamps/tokens
        self.peer_windows: Dict[str, deque] = {}
        # node_id -> tick count of anomalous variance
        self.violation_counts: Dict[str, int] = {}
        # quarantined/dropped nodes
        self.quarantined_peers: set = set()
        self._lock = threading.Lock()

    def record_message(self, node_id: str, metadata_feature: float) -> None:
        """Records a feature value from a peer's message metadata into a bounded deque with thread safety."""
        with self._lock:
            if node_id in self.quarantined_peers:
                return
            if node_id not in self.peer_windows:
                self.peer_windows[node_id] = deque(maxlen=self.window_size)
            self.peer_windows[node_id].append(metadata_feature)

    def calculate_entropy(self, values: List[float]) -> float:
        """Calculates Shannon entropy over discretized feature values."""
        if not values:
            return 0.0
        
        # Discretize continuous values into bins or frequency counts
        counts: Dict[Any, int] = {}
        total = len(values)
        for val in values:
            bucket = round(float(val), 2)
            counts[bucket] = counts.get(bucket, 0) + 1

        entropy = 0.0
        for count in counts.values():
            prob = count / total
            if prob > 0:
                entropy -= prob * math.log2(prob)
        return entropy

    def evaluate_peer(self, node_id: str) -> bool:
        """Evaluates a peer's recent message entropy against the threshold under lock.
        Returns True if the peer is flagged as a Sybil/abnormal node and should be dropped.
        """
        with self._lock:
            if node_id in self.quarantined_peers:
                return True

            window = self.peer_windows.get(node_id)
            if not window or len(window) < 5:
                return False

            ent = self.calculate_entropy(list(window))
            
            if ent < 0.3 or ent > self.entropy_threshold:
                violations = self.violation_counts.get(node_id, 0) + 1
                self.violation_counts[node_id] = violations
                if violations >= self.max_ticks_to_drop:
                    self.quarantined_peers.add(node_id)
                    return True
            else:
                if node_id in self.violation_counts:
                    self.violation_counts[node_id] = max(0, self.violation_counts[node_id] - 1)

            return False

    def is_quarantined(self, node_id: str) -> bool:
        with self._lock:
            return node_id in self.quarantined_peers
