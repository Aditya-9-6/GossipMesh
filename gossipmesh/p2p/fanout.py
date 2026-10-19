<<<<<<< HEAD
import time
from collections import deque
from typing import Dict, Any, Optional

class AdaptiveFanoutController:
    """Adapts the gossip broadcast fanout based on local peer message density and congestion."""
    def __init__(self, initial_fanout: int = 6, min_fanout: int = 2, max_fanout: int = 12, window_size: int = 50, target_rate: float = 5.0):
        self.fanout = initial_fanout
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout
        self.window_size = window_size
        self.target_rate = target_rate
        self.timestamps = deque(maxlen=window_size)
        self.duplicate_count = 0
        self.total_received = 0

    def record_message(self, is_duplicate: bool = False) -> int:
        now = time.time()
        self.timestamps.append(now)
        self.total_received += 1
        if is_duplicate:
            self.duplicate_count += 1
        return self.adapt()

    def adapt(self) -> int:
        if len(self.timestamps) < 5:
            return self.fanout
        
        duration = self.timestamps[-1] - self.timestamps[0]
        rate = len(self.timestamps) / duration if duration > 0 else float('inf')
        dup_ratio = self.duplicate_count / max(1, self.total_received)

        if rate > self.target_rate * 1.5 or dup_ratio > 0.3:
            self.fanout = max(self.min_fanout, self.fanout - 1)
        elif rate < self.target_rate * 0.8 and dup_ratio < 0.1:
            self.fanout = min(self.max_fanout, self.fanout + 1)
            
        return self.fanout

    def get_fanout(self) -> int:
        return self.fanout
=======
from typing import Dict, Any, Optional
from gossipmesh.p2p.matrix import EpidemicReachabilityMatrix

class DynamicFanoutController:
    """Computes localized message spread efficiency and adjusts node-specific
    dissemination fanout without causing flooding storms."""
    def __init__(self, node_id: str, base_fanout: int = 4, min_fanout: int = 1, max_fanout: int = 12) -> None:
        self.node_id = node_id
        self.base_fanout = base_fanout
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout
        self.matrix = EpidemicReachabilityMatrix(node_id)

    def compute_fanout(self) -> int:
        avg_reach = self.matrix.average_reachability()
        # If average reachability is high, we reduce fanout to save bandwidth;
        # if low, we increase fanout to ensure epidemic propagation.
        adjustment = int((0.5 - avg_reach) * 4)
        computed = self.base_fanout + adjustment
        return max(self.min_fanout, min(self.max_fanout, computed))

    def update_peer_feedback(self, peer_id: str, success: bool) -> None:
        self.matrix.record_ack(peer_id, success)

    get_metrics = lambda self: {
        "node_id": self.node_id,
        "current_fanout": self.compute_fanout(),
        "matrix": self.matrix.to_dict()
    }
>>>>>>> origin/main
