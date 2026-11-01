from typing import Dict, Any, Optional
import threading
import time


class EpidemicReachabilityMatrix:
    """Thread-safe epidemic reachability matrix tracking delivery latency, success probability,
    and topological stratum per peer for dynamic gossip fanout adaptation with O(1) amortized updates.
    """

    def __init__(self, node_id: str, alpha: float = 0.2) -> None:
        self.node_id = node_id
        self.alpha = alpha  # Exponential moving average smoothing factor
        self._lock = threading.Lock()
        # peer_id -> {"success_prob": float, "avg_latency": float, "stratum": str, "last_updated": float}
        self._peers: Dict[str, Dict[str, Any]] = {}

    def record_ack(self, peer_id: str, success: bool, latency: float = 0.0, stratum: str = "default") -> None:
        with self._lock:
            now = time.time()
            if peer_id not in self._peers:
                self._peers[peer_id] = {
                    "success_prob": 1.0 if success else 0.0,
                    "avg_latency": max(0.0, latency),
                    "stratum": stratum,
                    "last_updated": now,
                    "sample_count": 1,
                }
            else:
                p = self._peers[peer_id]
                target_val = 1.0 if success else 0.0
                p["success_prob"] = (1.0 - self.alpha) * p["success_prob"] + self.alpha * target_val
                if success and latency > 0:
                    p["avg_latency"] = (1.0 - self.alpha) * p["avg_latency"] + self.alpha * latency
                p["stratum"] = stratum
                p["last_updated"] = now
                p["sample_count"] += 1

    def average_reachability(self) -> float:
        with self._lock:
            if not self._peers:
                return 1.0
            total = sum(p["success_prob"] for p in self._peers.values())
            return total / len(self._peers)

    def stratum_reachability(self, stratum: str) -> float:
        with self._lock:
            stratum_peers = [p for p in self._peers.values() if p["stratum"] == stratum]
            if not stratum_peers:
                return 1.0
            return sum(p["success_prob"] for p in stratum_peers) / len(stratum_peers)

    def get_peer_metrics(self, peer_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._peers.get(peer_id)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "node_id": self.node_id,
                "average_reachability": self.average_reachability(),
                "peers": dict(self._peers),
            }
