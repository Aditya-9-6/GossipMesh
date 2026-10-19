import time
import threading
from collections import deque
from typing import Dict, List, Optional, Any


class PeerLivenessTracker:
    """Adaptive Windowed Heartbeat Ping-Pong Latency Matrix for Peer Liveness Tracking.
    Maintains bounded round-trip time (RTT) ring buffers per peer and computes
    exponentially weighted moving average (EWMA) health scores."""

    def __init__(self, window_size: int = 20, alpha: float = 0.3, max_ttl_ms: float = 5000.0):
        self.window_size = window_size
        self.alpha = alpha
        self.max_ttl_ms = max_ttl_ms
        self._lock = threading.Lock()
        self._rtt_buffers: Dict[str, deque] = {}
        self._last_seen: Dict[str, float] = {}
        self._pending_pings: Dict[str, float] = {}

    def record_ping_sent(self, peer_id: str) -> float:
        """Records the outgoing timestamp of a heartbeat ping to a peer."""
        now = time.time() * 1000.0
        with self._lock:
            self._pending_pings[peer_id] = now
        return now

    def record_pong_received(self, peer_id: str) -> Optional[float]:
        """Records a returning pong, computes RTT, updates windowed buffer and EWMA."""
        now = time.time() * 1000.0
        with self._lock:
            sent_time = self._pending_pings.pop(peer_id, None)
            if sent_time is None:
                return None
            rtt = max(0.0, now - sent_time)
            self._last_seen[peer_id] = now

            if peer_id not in self._rtt_buffers:
                self._rtt_buffers[peer_id] = deque(maxlen=self.window_size)
            self._rtt_buffers[peer_id].append(rtt)
            return rtt

    def get_ewma_latency(self, peer_id: str) -> float:
        """Calculates the Exponentially Weighted Moving Average RTT for a peer."""
        with self._lock:
            buffer = self._rtt_buffers.get(peer_id)
            if not buffer:
                return self.max_ttl_ms

            ewma = buffer[0]
            for rtt in list(buffer)[1:]:
                ewma = self.alpha * rtt + (1 - self.alpha) * ewma
            return ewma

    def get_health_score(self, peer_id: str) -> float:
        """Computes composite health score [0.0, 1.0] isolating silent network partitions."""
        with self._lock:
            last = self._last_seen.get(peer_id)
            if last is None:
                return 0.0
            now = time.time() * 1000.0
            elapsed = now - last
            if elapsed > self.max_ttl_ms:
                return 0.0

            ewma = self.get_ewma_latency(peer_id)
            # Score decays as latency approaches max_ttl_ms and time since last seen increases
            latency_factor = max(0.0, 1.0 - (ewma / self.max_ttl_ms))
            recency_factor = max(0.0, 1.0 - (elapsed / self.max_ttl_ms))
            return float(0.6 * latency_factor + 0.4 * recency_factor)

    def is_healthy(self, peer_id: str, threshold: float = 0.2) -> bool:
        """Determines if a peer is considered healthy based on composite score."""
        return self.get_health_score(peer_id) >= threshold

    def get_active_peers(self, threshold: float = 0.2) -> List[str]:
        """Returns a list of all currently healthy active peers."""
        with self._lock:
            peers = list(self._last_seen.keys())
        return [p for p in peers if self.is_healthy(p, threshold)]
