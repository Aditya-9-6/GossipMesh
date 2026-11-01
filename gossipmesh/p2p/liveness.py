import time
import threading
from typing import Dict, Any, List, Optional


class LivenessConfig:
    def __init__(
        self,
        window_size: int = 50,
        ewma_alpha: float = 0.3,
        timeout_threshold_ms: float = 1000.0,
        quarantine_failure_count: int = 3,
    ) -> None:
        self.window_size = window_size
        self.ewma_alpha = ewma_alpha
        self.timeout_threshold_ms = timeout_threshold_ms
        self.quarantine_failure_count = quarantine_failure_count


class SlidingWindowEWMA:
    def __init__(self, capacity: int = 50, alpha: float = 0.3) -> None:
        self.capacity = capacity
        self.alpha = alpha
        self._samples: List[float] = []
        self._ewma: float = 0.0
        self._lock = threading.Lock()

    def add_sample(self, value: float) -> float:
        with self._lock:
            self._samples.append(value)
            if len(self._samples) > self.capacity:
                self._samples.pop(0)
            if self._ewma == 0.0:
                self._ewma = value
            else:
                self._ewma = self.alpha * value + (1.0 - self.alpha) * self._ewma
            return self._ewma

    def get_ewma(self) -> float:
        with self._lock:
            return self._ewma

    def get_samples(self) -> List[float]:
        with self._lock:
            return list(self._samples)


class PeerLivenessTracker:
    def __init__(self, config: Optional[LivenessConfig] = None) -> None:
        self.config = config or LivenessConfig()
        self.latency_matrix: Dict[str, SlidingWindowEWMA] = {}
        self.consecutive_failures: Dict[str, int] = {}
        self.quarantined_peers: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def record_ping(self, peer_id: str, rtt_ms: Optional[float], timed_out: bool = False) -> Dict[str, Any]:
        with self._lock:
            if peer_id not in self.latency_matrix:
                self.latency_matrix[peer_id] = SlidingWindowEWMA(
                    capacity=self.config.window_size, alpha=self.config.ewma_alpha
                )
                self.consecutive_failures[peer_id] = 0
                self.quarantined_peers[peer_id] = False

            ewma_tracker = self.latency_matrix[peer_id]

            if timed_out or rtt_ms is None or rtt_ms > self.config.timeout_threshold_ms:
                self.consecutive_failures[peer_id] += 1
                if self.consecutive_failures[peer_id] >= self.config.quarantine_failure_count:
                    self.quarantined_peers[peer_id] = True
                current_ewma = ewma_tracker.get_ewma()
            else:
                self.consecutive_failures[peer_id] = 0
                self.quarantined_peers[peer_id] = False
                current_ewma = ewma_tracker.add_sample(rtt_ms)

            return {
                "peer_id": peer_id,
                "ewma_latency_ms": current_ewma,
                "consecutive_failures": self.consecutive_failures[peer_id],
                "is_quarantined": self.quarantined_peers[peer_id],
                "timestamp": time.time(),
            }

    def is_peer_quarantined(self, peer_id: str) -> bool:
        with self._lock:
            return self.quarantined_peers.get(peer_id, False)

    def get_peer_metrics(self, peer_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if peer_id not in self.latency_matrix:
                return None
            return {
                "peer_id": peer_id,
                "ewma_latency_ms": self.latency_matrix[peer_id].get_ewma(),
                "consecutive_failures": self.consecutive_failures.get(peer_id, 0),
                "is_quarantined": self.quarantined_peers.get(peer_id, False),
                "samples": self.latency_matrix[peer_id].get_samples(),
            }

    def get_global_matrix_status(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {pid: self.get_peer_metrics(pid) for pid in self.latency_matrix}
