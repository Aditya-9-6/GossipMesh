import logging
from typing import List, Any
from dataclasses import dataclass, field
from gossipmesh.p2p.fanout import AdaptiveFanoutController

logger = logging.getLogger(__name__)

@dataclass
class TransportTelemetry:
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    duplicates_detected: int = 0
    active_connections: int = 0

class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls."""
    def __init__(self, node_id: str, initial_fanout: int = 6):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.telemetry = TransportTelemetry()

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected
