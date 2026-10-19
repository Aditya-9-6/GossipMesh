import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class PeerHealthConfig:
    alpha_latency: float = 0.2
    alpha_drop: float = 0.2
    alpha_violation: float = 0.3
    quarantine_threshold: float = 40.0
    recovery_threshold: float = 75.0
    max_violations: int = 10


@dataclass
class PeerHealthMetrics:
    ewma_latency: float = 0.0
    ewma_drop_rate: float = 0.0
    ewma_violation_rate: float = 0.0
    health_score: float = 100.0
    is_quarantined: bool = False
    total_samples: int = 0
    last_updated: float = field(default_factory=time.time)


class SlidingWindowPeerHealthScorecard:
    def __init__(self, config: Optional[PeerHealthConfig] = None) -> None:
        self.config = config or PeerHealthConfig()
        self.metrics = PeerHealthMetrics()
        self._lock = threading.Lock()

    def record_sample(self, latency_ms: float, dropped: bool, violated: bool) -> float:
        with self._lock:
            m = self.metrics
            m.total_samples += 1
            m.last_updated = time.time()

            if m.total_samples == 1:
                m.ewma_latency = latency_ms
                m.ewma_drop_rate = 1.0 if dropped else 0.0
                m.ewma_violation_rate = 1.0 if violated else 0.0
            else:
                a_l = self.config.alpha_latency
                a_d = self.config.alpha_drop
                a_v = self.config.alpha_violation

                m.ewma_latency = a_l * latency_ms + (1.0 - a_l) * m.ewma_latency
                drop_val = 1.0 if dropped else 0.0
                m.ewma_drop_rate = a_d * drop_val + (1.0 - a_d) * m.ewma_drop_rate
                viot_val = 1.0 if violated else 0.0
                m.ewma_violation_rate = a_v * viot_val + (1.0 - a_v) * m.ewma_violation_rate

            # Score calculation: 100 base, penalized by latency, drops, and violations
            lat_penalty = min(50.0, (m.ewma_latency / 100.0) * 15.0)
            drop_penalty = m.ewma_drop_rate * 40.0
            viot_penalty = m.ewma_violation_rate * 50.0

            score = max(0.0, 100.0 - (lat_penalty + drop_penalty + viot_penalty))
            m.health_score = score

            if not m.is_quarantined and score <= self.config.quarantine_threshold:
                m.is_quarantined = True
            elif m.is_quarantined and score >= self.config.recovery_threshold:
                m.is_quarantined = False

            return m.health_score

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            m = self.metrics
            return {
                "ewma_latency": m.ewma_latency,
                "ewma_drop_rate": m.ewma_drop_rate,
                "ewma_violation_rate": m.ewma_violation_rate,
                "health_score": m.health_score,
                "is_quarantined": m.is_quarantined,
                "total_samples": m.total_samples,
                "last_updated": m.last_updated,
            }

    def reset(self) -> None:
        with self._lock:
            self.metrics = PeerHealthMetrics()
