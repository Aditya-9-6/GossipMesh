from typing import Dict, List, Optional, Any
from gossipmesh.p2p.entropy import AntiEntropyEngine, AntiEntropyScraper


class MeshSyncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.engine = AntiEntropyEngine(node_id=node_id)

    def sync_state(self, peer_id: str, peer_state: Dict[str, Any]) -> List[str]:
        return self.engine.reconcile_divergence(peer_state)
