import time
from typing import Dict, List, Optional

class PeerScore:
    def __init__(self, node_id: str, window_size: int = 100, reputation_threshold: float = 0.4):
        self.node_id = node_id
        self.window_size = window_size
        self.reputation_threshold = reputation_threshold
        self.latencies: List[float] = []
        self.valid_messages: int = 0
        self.invalid_messages: int = 0
        self.protocol_errors: int = 0
        self.blacklisted: bool = False
        self.last_updated: float = time.time()

    def record_interaction(self, latency: float, valid: bool, protocol_error: bool = False) -> None:
        self.latencies.append(latency)
        if len(self.latencies) > self.window_size:
            self.latencies.pop(0)
        
        if valid:
            self.valid_messages += 1
        else:
            self.invalid_messages += 1
            
        if protocol_error:
            self.protocol_errors += 1
            
        self.last_updated = time.time()
        self._evaluate_blacklisting()

    def compute_score(self) -> float:
        total_msgs = self.valid_messages + self.invalid_messages
        if total_msgs == 0:
            return 1.0
        
        validity_ratio = self.valid_messages / total_msgs
        error_penalty = (self.protocol_errors * 0.5) / max(total_msgs, 1)
        
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0.0
        latency_penalty = min(avg_latency / 10.0, 0.3)
        
        score = max(0.0, validity_ratio - error_penalty - latency_penalty)
        return float(score)

    def _evaluate_blacklisting(self) -> None:
        if self.compute_score() < self.reputation_threshold:
            self.blacklisted = True

class ScoringRegistry:
    def __init__(self, window_size: int = 100, reputation_threshold: float = 0.4):
        self.window_size = window_size
        self.reputation_threshold = reputation_threshold
        self.scores: Dict[str, PeerScore] = {}

    def get_or_create(self, node_id: str) -> PeerScore:
        if node_id not in self.scores:
            self.scores[node_id] = PeerScore(node_id, self.window_size, self.reputation_threshold)
        return self.scores[node_id]

    def record(self, node_id: str, latency: float, valid: bool, protocol_error: bool = False) -> PeerScore:
        score = self.get_or_create(node_id)
        score.record_interaction(latency, valid, protocol_error)
        return score

    def is_blacklisted(self, node_id: str) -> bool:
        score = self.scores.get(node_id)
        return score.blacklisted if score else False
