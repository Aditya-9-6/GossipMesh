import time
import threading
from typing import Dict, Tuple

class PeerMetricsTracker:
    """Tracks rolling round-trip times (RTT) and congestion signals for P2P peers
    with automatic expiration of stale telemetry metrics to prevent memory bloat.
    """
    def __init__(self, stale_threshold_sec: float = 60.0):
        self._rtt_data: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()
        self._stale_threshold = stale_threshold_sec

    def record_rtt(self, peer_id: str, rtt: float) -> None:
        with self._lock:
            self._rtt_data[peer_id] = (rtt, time.time())

    def get_rtt(self, peer_id: str) -> float:
        with self._lock:
            entry = self._rtt_data.get(peer_id)
            if not entry:
                return 0.0
            rtt, timestamp = entry
            if time.time() - timestamp > self._stale_threshold:
                del self._rtt_data[peer_id]
                return 0.0
            return rtt

    def cleanup_stale(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            stale_keys = [
                pid for pid, (_, ts) in self._rtt_data.items()
                if now - ts > self._stale_threshold
            ]
            for pid in stale_keys:
                del self._rtt_data[pid]
                removed += 1
        return removed
