import random
from typing import List, Dict, Optional
from gossipmesh.p2p.metrics import PeerMetricsRegistry

class PeerSelector:
    """Selects peers for gossip dissemination prioritizing low-latency nodes via windowed EMA."""
    def __init__(self, metrics_registry: PeerMetricsRegistry, default_latency_penalty: float = 1000.0):
        self.metrics_registry = metrics_registry
        self.default_latency_penalty = default_latency_penalty

    def select_peers(self, available_peers: List[str], count: int, strategy: str = "hybrid", exploration_ratio: float = 0.2) -> List[str]:
        """Selects a subset of peers for epidemic fanout based on latency and random exploration."""
        if not available_peers:
            return []
        
        if count >= len(available_peers):
            return list(available_peers)

        if strategy == "random":
            return random.sample(available_peers, count)

        emas = self.metrics_registry.get_all_emas()

        # Sort peers by EMA latency (ascending; lower latency is better)
        scored_peers = []
        for peer in available_peers:
            lat = emas.get(peer, self.default_latency_penalty)
            scored_peers.append((peer, lat))

        scored_peers.sort(key=lambda x: x[1])

        num_exploration = max(1, int(count * exploration_ratio)) if strategy == "hybrid" else 0
        num_exploitation = count - num_exploration

        # Exploitation set: lowest latency peers
        exploitation_pool = [p[0] for p in scored_peers[:max(0, len(scored_peers) - num_exploration)]]
        selected = random.sample(exploitation_pool, min(num_exploitation, len(exploitation_pool)))

        # Exploration set: random remaining peers
        remaining_pool = [p for p in available_peers if p not in selected]
        if num_exploration > 0 and remaining_pool:
            exploring = random.sample(remaining_pool, min(num_exploration, len(remaining_pool)))
            selected.extend(exploring)

        # Ensure we return exact count if possible
        if len(selected) < count:
            leftovers = [p for p in available_peers if p not in selected]
            selected.extend(random.sample(leftovers, count - len(selected)))

        return selected[:count]
