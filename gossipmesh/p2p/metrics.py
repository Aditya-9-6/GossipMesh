import threading
from collections import deque
from typing import Any, Dict, List, Optional


class EMALatencyTracker:
    """Tracks round-trip latency using a windowed Exponential Moving Average (EMA) with bounded memory."""

    def __init__(self, window_size: int = 50, alpha: float = 0.2):
        self.window_size = window_size
        self.alpha = alpha
        self.latencies: deque = deque(maxlen=window_size)
        self.current_ema: Optional[float] = None

    def record(self, latency_ms: float) -> float:
        """Records a new latency measurement and updates the EMA."""
        if latency_ms < 0:
            raise ValueError("Latency cannot be negative")
        self.latencies.append(latency_ms)
        if self.current_ema is None:
            self.current_ema = latency_ms
        else:
            self.current_ema = self.alpha * latency_ms + (1 - self.alpha) * self.current_ema
        return self.current_ema

    @property
    def ema(self) -> Optional[float]:
        return self.current_ema

    def get_stats(self) -> Dict[str, Any]:
        return {"ema": self.current_ema, "samples": len(self.latencies), "recent": list(self.latencies)}


class PeerMetricsRegistry:
    """Thread-safe registry for managing peer EMA latency trackers."""

    def __init__(self, window_size: int = 50, alpha: float = 0.2):
        self.window_size = window_size
        self.alpha = alpha
        self._trackers: Dict[str, EMALatencyTracker] = {}
        self._lock = threading.Lock()

    def record_latency(self, peer_id: str, latency_ms: float) -> float:
        with self._lock:
            if peer_id not in self._trackers:
                self._trackers[peer_id] = EMALatencyTracker(window_size=self.window_size, alpha=self.alpha)
            return self._trackers[peer_id].record(latency_ms)

    def get_ema(self, peer_id: str) -> Optional[float]:
        with self._lock:
            tracker = self._trackers.get(peer_id)
            return tracker.ema if tracker else None

    def get_all_emas(self) -> Dict[str, float]:
        with self._lock:
            return {pid: t.ema for pid, t in self._trackers.items() if t.ema is not None}
