import time
import threading
from typing import Dict, Any, Optional


class ReputationConfig:
    def __init__(
        self,
        half_life_seconds: float = 300.0,
        initial_score: float = 100.0,
        min_score: float = 0.0,
        max_score: float = 200.0,
        quarantine_threshold: float = 30.0,
        latency_weight: float = 0.3,
        integrity_weight: float = 0.4,
        contribution_weight: float = 0.3,
        violation_penalty: float = 25.0,
        drop_penalty: float = 10.0,
    ) -> None:
        self.half_life_seconds = half_life_seconds
        self.initial_score = initial_score
        self.min_score = min_score
        self.max_score = max_score
        self.quarantine_threshold = quarantine_threshold
        self.latency_weight = latency_weight
        self.integrity_weight = integrity_weight
        self.contribution_weight = contribution_weight
        self.violation_penalty = violation_penalty
        self.drop_penalty = drop_penalty


class AdaptivePeerReputationEngine:
    def __init__(self, config: Optional[ReputationConfig] = None) -> None:
        self.config = config or ReputationConfig()
        self._scores: Dict[str, float] = {}
        self._last_updated: Dict[str, float] = {}
        self._violation_counts: Dict[str, int] = {}
        self._contribution_counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def _decay_score(self, peer_id: str, now: float) -> float:
        score = self._scores.get(peer_id, self.config.initial_score)
        last = self._last_updated.get(peer_id, now)
        elapsed = max(0.0, now - last)
        if elapsed > 0.0 and self.config.half_life_seconds > 0:
            decay_factor = 0.5 ** (elapsed / self.config.half_life_seconds)
            # Pull score gradually towards initial baseline under decay
            score = self.config.initial_score + (score - self.config.initial_score) * decay_factor
        self._last_updated[peer_id] = now
        self._scores[peer_id] = score
        return score

    def record_interaction(
        self,
        peer_id: str,
        latency_ms: float,
        payload_valid: bool = True,
        gossip_contributed: bool = False,
        violated: bool = False,
        dropped: bool = False,
    ) -> float:
        now = time.time()
        with self._lock:
            score = self._decay_score(peer_id, now)

            delta = 0.0
            if violated:
                delta -= self.config.violation_penalty
                self._violation_counts[peer_id] = self._violation_counts.get(peer_id, 0) + 1
            if dropped:
                delta -= self.config.drop_penalty

            # Latency component: reward sub-50ms, penalize >500ms
            if not violated and not dropped:
                if latency_ms <= 50.0:
                    delta += 2.0
                elif latency_ms >= 500.0:
                    delta -= 5.0

            if payload_valid:
                delta += 3.0
            else:
                delta -= 15.0

            if gossip_contributed:
                delta += 5.0
                self._contribution_counts[peer_id] = self._contribution_counts.get(peer_id, 0) + 1

            score = max(self.config.min_score, min(self.config.max_score, score + delta))
            self._scores[peer_id] = score
            return score

    def get_score(self, peer_id: str) -> float:
        now = time.time()
        with self._lock:
            return self._decay_score(peer_id, now)

    def is_quarantined(self, peer_id: str) -> bool:
        score = self.get_score(peer_id)
        return score < self.config.quarantine_threshold

    def get_metrics(self, peer_id: str) -> Dict[str, Any]:
        score = self.get_score(peer_id)
        with self._lock:
            violations = self._violation_counts.get(peer_id, 0)
            contributions = self._contribution_counts.get(peer_id, 0)
            quarantined = score < self.config.quarantine_threshold
            return {
                "peer_id": peer_id,
                "reputation_score": round(score, 2),
                "is_quarantined": quarantined,
                "violation_count": violations,
                "contribution_count": contributions,
            }
