import time
import asyncio
from typing import Dict, Any, Optional
from gossipmesh.p2p.health import PeerHealthMonitor, PeerHealthConfig, PeerHealthScorecard

class PeerNode:
    def __init__(self, peer_id: str, address: str, health_monitor: Optional[PeerHealthMonitor] = None) -> None:
        self.peer_id = peer_id
        self.address = address
        self.health_monitor = health_monitor or PeerHealthMonitor()
        self.connected_at = time.time()
        self.last_seen = time.time()

    def record_interaction(self, latency: float, dropped: bool = False, violated: bool = False) -> PeerHealthScorecard:
        self.last_seen = time.time()
        return self.health_monitor.record_metric(self.peer_id, latency, dropped, violated)

    def is_healthy(self) -> bool:
        return self.health_monitor.is_peer_healthy(self.peer_id)

    def get_health_scorecard(self) -> Optional[PeerHealthScorecard]:
        return self.health_monitor.get_scorecard(self.peer_id)

    def to_dict(self) -> Dict[str, Any]:
        sc = self.get_health_scorecard()
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "connected_at": self.connected_at,
            "last_seen": self.last_seen,
            "healthy": self.is_healthy(),
            "scorecard": {
                "overall_score": sc.overall_score if sc else 1.0,
                "is_quarantined": sc.is_quarantined if sc else False,
            } if sc else None
        }
