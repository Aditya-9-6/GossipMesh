import time
from typing import Dict, Tuple

class PeerMetricsRegistry:
    """Tracks rolling round-trip times (RTT) and message delivery success/failure for P2P peers."""
    def __init__(self, ttl_seconds: float = 300.0, alpha: float = 0.2):
        self.ttl_seconds = ttl_seconds
        self.alpha = alpha
        self._metrics: Dict[str, Dict[str, float]] = {}

    def record_rtt(self, peer_id: str, rtt: float) -> None:
        now = time.time()
        if peer_id not in self._metrics:
            self._metrics[peer_id] = {
                "rtt": rtt,
                "smoothed_rtt": rtt,
                "failures": 0.0,
                "last_updated": now,
            }
        else:
            m = self._metrics[peer_id]
            m["rtt"] = rtt
            m["smoothed_rtt"] = self.alpha * rtt + (1 - self.alpha) * m["smoothed_rtt"]
            m["last_updated"] = now

    def record_failure(self, peer_id: str) -> None:
        now = time.time()
        if peer_id not in self._metrics:
            self._metrics[peer_id] = {
                "rtt": 1.0,
                "smoothed_rtt": 1.0,
                "failures": 1.0,
                "last_updated": now,
            }
        else:
            self._metrics[peer_id]["failures"] += 1.0
            self._metrics[peer_id]["last_updated"] = now

    def get_metrics(self, peer_id: str) -> Tuple[float, float]:
        self.expire_stale()
        m = self._metrics.get(peer_id)
        if not m:
            return (0.1, 0.0)
        return (m["smoothed_rtt"], m["failures"])

    def expire_stale(self) -> None:
        now = time.time()
        stale_keys = [
            pid for pid, data in self._metrics.items()
            if now - data["last_updated"] > self.ttl_seconds
        ]
        for pid in stale_keys:
            del self._metrics[pid]

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
