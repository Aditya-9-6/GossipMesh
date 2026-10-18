from typing import List
from gossipmesh.p2p.adaptive_fanout import AdaptiveFanoutManager

class GossipTransport:
    def __init__(self, min_fanout: int = 3, max_fanout: int = 15, default_fanout: int = 6):
        self.fanout_manager = AdaptiveFanoutManager(min_fanout=min_fanout, max_fanout=max_fanout, default_fanout=default_fanout)

    def record_peer_telemetry(self, latency_ms: float, drop_rate: float):
        self.fanout_manager.record_metrics(latency_ms, drop_rate)

    def select_gossip_peers(self, all_peers: List[str]) -> List[str]:
        return self.fanout_manager.get_adaptive_targets(all_peers)
