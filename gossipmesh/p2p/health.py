import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class PeerHealthConfig:
    alpha: float = 0.2
    quarantine_threshold: float = 0.4
    recovery_threshold: float = 0.7
    max_history_window: int = 100

@dataclass
class PeerHealthScorecard:
    peer_id: str
    latency_ewma: float = 0.0
    drop_rate_ewma: float = 0.0
    violation_score: float = 0.0
    overall_score: float = 1.0
    is_quarantined: bool = False
    last_updated: float = field(default_factory=time.time)

class PeerHealthMonitor:
    def __init__(self, config: Optional[PeerHealthConfig] = None) -> None:
        self.config = config or PeerHealthConfig()
        self._lock = threading.Lock()
        self._scorecards: Dict[str, PeerHealthScorecard] = {}

    def record_metric(self, peer_id: str, latency: float, dropped: bool, violated: bool) -> PeerHealthScorecard:
        with self._lock:
            if peer_id not in self._scorecards:
                self._scorecards[peer_id] = PeerHealthScorecard(peer_id=peer_id)
            sc = self._scorecards[peer_id]
            alpha = self.config.alpha
            sc.latency_ewma = (alpha * latency) + ((1.0 - alpha) * sc.latency_ewma)
            drop_val = 1.0 if dropped else 0.0
            sc.drop_rate_ewma = (alpha * drop_val) + ((1.0 - alpha) * sc.drop_rate_ewma)
            viol_val = 1.0 if violated else 0.0
            sc.violation_score = (alpha * viol_val) + ((1.0 - alpha) * sc.violation_score)
            
            lat_penalty = min(sc.latency_ewma / 1.0, 1.0)
            drop_penalty = sc.drop_rate_ewma
            viol_penalty = sc.violation_score
            raw_health = 1.0 - (0.4 * lat_penalty + 0.4 * drop_penalty + 0.2 * viol_penalty)
            sc.overall_score = max(0.0, min(1.0, raw_health))
            sc.last_updated = time.time()
            
            if not sc.is_quarantined and sc.overall_score < self.config.quarantine_threshold:
                sc.is_quarantined = True
            elif sc.is_quarantined and sc.overall_score >= self.config.recovery_threshold:
                sc.is_quarantined = False
            return sc

    def get_scorecard(self, peer_id: str) -> Optional[PeerHealthScorecard]:
        with self._lock:
            return self._scorecards.get(peer_id)

    def is_peer_healthy(self, peer_id: str) -> bool:
        with self._lock:
            sc = self._scorecards.get(peer_id)
            if not sc:
                return True
            return not sc.is_quarantined

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {pid: {
                "latency_ewma": sc.latency_ewma,
                "drop_rate_ewma": sc.drop_rate_ewma,
                "violation_score": sc.violation_score,
                "overall_score": sc.overall_score,
                "is_quarantined": sc.is_quarantined,
                "last_updated": sc.last_updated
            } for pid, sc in self._scorecards.items()}
