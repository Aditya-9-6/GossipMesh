import time
from typing import Dict

class PeerMetricsTracker:
    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha
        self.rtt_map: Dict[str, float] = {}
        self.queue_depth_map: Dict[str, int] = {}

    def update_rtt(self, peer_id: str, rtt: float) -> float:
        current = self.rtt_map.get(peer_id, rtt)
        updated = (1 - self.alpha) * current + self.alpha * rtt
        self.rtt_map[peer_id] = updated
        return updated

    def update_queue_depth(self, peer_id: str, depth: int) -> int:
        self.queue_depth_map[peer_id] = depth
        return depth

    def get_rtt(self, peer_id: str) -> float:
        return self.rtt_map.get(peer_id, 0.0)

    def get_queue_depth(self, peer_id: str) -> int:
        return self.queue_depth_map.get(peer_id, 0)
