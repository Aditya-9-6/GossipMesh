import time
from collections import deque
from typing import Dict, List, Tuple

class AdaptiveFanoutManager:
    def __init__(self, min_fanout: int = 3, max_fanout: int = 15, default_fanout: int = 6, window_size: int = 50):
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout
        self.default_fanout = default_fanout
        self.window_size = window_size
        self.latencies: deque = deque(maxlen=window_size)
        self.drop_rates: deque = deque(maxlen=window_size)

    def record_metrics(self, latency_ms: float, drop_rate: float):
        self.latencies.append(latency_ms)
        self.drop_rates.append(drop_rate)

    def compute_fanout(self) -> int:
        if not self.latencies or not self.drop_rates:
            return self.default_fanout
        
        avg_latency = sum(self.latencies) / len(self.latencies)
        avg_drop = sum(self.drop_rates) / len(self.drop_rates)
        
        fanout = self.default_fanout
        if avg_latency > 250.0 or avg_drop > 0.15:
            fanout += 2
        elif avg_latency < 80.0 and avg_drop < 0.02:
            fanout -= 1
            
        return max(self.min_fanout, min(self.max_fanout, fanout))

    def get_adaptive_targets(self, peers: List[str]) -> List[str]:
        target_count = self.compute_fanout()
        return peers[:target_count]
