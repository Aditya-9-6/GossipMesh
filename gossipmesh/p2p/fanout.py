from typing import Dict, Any, Optional
import threading
from gossipmesh.p2p.reachability import EpidemicReachabilityMatrix


class DynamicFanoutController:
    """Computes localized message spread efficiency and adjusts node-specific
    dissemination fanout without causing flooding storms using a PID-controlled feedback loop.
    """

    def __init__(self, node_id: str, base_fanout: int = 4, min_fanout: int = 1, max_fanout: int = 12) -> None:
        self.node_id = node_id
        self.base_fanout = base_fanout
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout
        self.matrix = EpidemicReachabilityMatrix(node_id)
        self._lock = threading.Lock()
        # PID state variables
        self._integral = 0.0
        self._last_error = 0.0

    def compute_fanout(self, stratum: Optional[str] = None) -> int:
        with self._lock:
            avg_reach = self.matrix.stratum_reachability(stratum) if stratum else self.matrix.average_reachability()
            # Target reachability is 0.9. Error = Target - Actual
            error = 0.9 - avg_reach
            self._integral += error
            derivative = error - self._last_error
            self._last_error = error

            # PID coefficients
            kp, ki, kd = 3.0, 0.1, 0.05
            adjustment = int((kp * error) + (ki * self._integral) + (kd * derivative))
            computed = self.base_fanout + adjustment
            return max(self.min_fanout, min(self.max_fanout, computed))

    def update_peer_feedback(self, peer_id: str, success: bool, latency: float = 0.0, stratum: str = "default") -> None:
        with self._lock:
            self.matrix.record_ack(peer_id, success, latency=latency, stratum=stratum)

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "node_id": self.node_id,
                "current_fanout": self.compute_fanout(),
                "matrix": self.matrix.to_dict(),
            }
