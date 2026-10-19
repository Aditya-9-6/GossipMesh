from typing import Dict, Any


class VectorClockEntropy:
    """Computes vector clock divergence and entropy between mesh peers."""

    def __init__(self, node_id: str):
        self.node_id = node_id

    def compute_divergence(self, local_clock: Dict[str, int], peer_clock: Dict[str, int]) -> float:
        keys = set(local_clock.keys()).union(set(peer_clock.keys()))
        if not keys:
            return 0.0
        diff = 0
        for k in keys:
            v_local = local_clock.get(k, 0)
            v_peer = peer_clock.get(k, 0)
            diff += abs(v_local - v_peer)
        return float(diff) / float(len(keys))


class AntiEntropySyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)

    def sync_clocks(self, local_clock: dict, peer_clock: dict) -> float:
        return self.entropy.compute_divergence(local_clock, peer_clock)
