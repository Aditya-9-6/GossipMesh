from typing import Dict, Any, Optional
from gossipmesh.p2p.scoring import ScoringRegistry

class P2PTransport:
    def __init__(self, node_id: str, scoring_registry: Optional[ScoringRegistry] = None):
        self.node_id = node_id
        self.scoring_registry = scoring_registry or ScoringRegistry()

    def send_message(self, target_node_id: str, payload: Dict[str, Any]) -> bool:
        if self.scoring_registry.is_blacklisted(target_node_id):
            return False
        return True

    def receive_message(self, source_node_id: str, payload: Dict[str, Any], latency: float, valid: bool, protocol_error: bool = False) -> bool:
        self.scoring_registry.record(source_node_id, latency, valid, protocol_error)
        if self.scoring_registry.is_blacklisted(source_node_id):
            return False
        return True
