import time
from typing import Dict, Tuple

class PeerMetricsRegistry:
    """Tracks rolling round-trip times (RTT) and message delivery success/failure for P2P peers."""
    def __init__(self, ttl_seconds: float = 300.0, alpha: float = 0.2, max_peers: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.alpha = alpha
        self.max_peers = max_peers
        self._metrics: Dict[str, Dict[str, float]] = {}

    def record_rtt(self, peer_id: str, rtt: float) -> None:
        self.expire_stale()
        now = time.time()
        if peer_id not in self._metrics:
            if len(self._metrics) >= self.max_peers:
                self._evict_oldest()
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
        self.expire_stale()
        now = time.time()
        if peer_id not in self._metrics:
            if len(self._metrics) >= self.max_peers:
                self._evict_oldest()
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

    def _evict_oldest(self) -> None:
        if not self._metrics:
            return
        oldest_pid = min(self._metrics.keys(), key=lambda k: self._metrics[k]["last_updated"])
        del self._metrics[oldest_pid]


class PeerMetricsTracker:
    """Tracks peer round-trip times and queue depths with TTL and size eviction bounds."""
    def __init__(self, alpha: float = 0.2, ttl_seconds: float = 300.0, max_peers: int = 1000):
        self.alpha = alpha
        self.ttl_seconds = ttl_seconds
        self.max_peers = max_peers
        self.rtt_map: Dict[str, float] = {}
        self.queue_depth_map: Dict[str, int] = {}
        self.last_updated: Dict[str, float] = {}

    def _expire_stale(self) -> None:
        now = time.time()
        stale = [
            pid for pid, ts in self.last_updated.items()
            if now - ts > self.ttl_seconds
        ]
        for pid in stale:
            self.rtt_map.pop(pid, None)
            self.queue_depth_map.pop(pid, None)
            self.last_updated.pop(pid, None)

    def _enforce_capacity(self) -> None:
        if len(self.rtt_map) >= self.max_peers and self.last_updated:
            oldest = min(self.last_updated.keys(), key=lambda k: self.last_updated[k])
            self.rtt_map.pop(oldest, None)
            self.queue_depth_map.pop(oldest, None)
            self.last_updated.pop(oldest, None)

    def update_rtt(self, peer_id: str, rtt: float) -> float:
        self._expire_stale()
        now = time.time()
        if peer_id not in self.rtt_map and len(self.rtt_map) >= self.max_peers:
            self._enforce_capacity()

        current = self.rtt_map.get(peer_id, rtt)
        updated = (1 - self.alpha) * current + self.alpha * rtt
        self.rtt_map[peer_id] = updated
        self.last_updated[peer_id] = now
        return updated

    def update_queue_depth(self, peer_id: str, depth: int) -> int:
        self._expire_stale()
        now = time.time()
        if peer_id not in self.queue_depth_map and len(self.queue_depth_map) >= self.max_peers:
            self._enforce_capacity()

        self.queue_depth_map[peer_id] = depth
        self.last_updated[peer_id] = now
        return depth

    def get_rtt(self, peer_id: str) -> float:
        self._expire_stale()
        return self.rtt_map.get(peer_id, 0.0)

    def get_queue_depth(self, peer_id: str) -> int:
        self._expire_stale()
        return self.queue_depth_map.get(peer_id, 0)
