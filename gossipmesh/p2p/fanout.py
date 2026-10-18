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
