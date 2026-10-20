import time
from typing import Dict, Any, List


class EpidemicReachabilityMatrix:
    """Decentralized epidemic reachability matrix tracking message propagation
    probabilities and reachability metrics across mesh nodes."""

    def __init__(self, node_id: str, decay_factor: float = 0.95) -> None:
        self.node_id = node_id
        self.decay_factor = decay_factor
        self.reachability: Dict[str, float] = {}
        self.last_updated: Dict[str, float] = {}

    def record_ack(self, peer_id: str, success: bool = True) -> None:
        current_val = self.reachability.get(peer_id, 0.5)
        increment = 0.1 if success else -0.15
        new_val = max(0.0, min(1.0, current_val * self.decay_factor + increment))
        self.reachability[peer_id] = new_val
        self.last_updated[peer_id] = time.time()

    def get_reachability(self, peer_id: str) -> float:
        return self.reachability.get(peer_id, 0.5)

    def average_reachability(self) -> float:
        if not self.reachability:
            return 0.5
        return sum(self.reachability.values()) / len(self.reachability)

    to_dict = lambda self: {
        "node_id": self.node_id,
        "reachability": self.reachability,
        "average": self.average_reachability(),
    }
