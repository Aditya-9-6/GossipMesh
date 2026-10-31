"""
Decentralized adaptive heartbeat manager integrating backoff state tracking across mesh peers.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from gossipmesh.consensus.backoff import AdaptiveBackoffConfig, NodeHeartbackoffState


class MeshHeartbeatManager:
    """Manages decentralized heartbeat pings and adaptive backoff for all connected peers."""

    def __init__(self, config: Optional[AdaptiveBackoffConfig] = None):
        self.config = config or AdaptiveBackoffConfig()
        self.peer_states: Dict[str, NodeHeartbackoffState] = {}

    def get_or_create_peer(self, node_id: str) -> NodeHeartbackoffState:
        if node_id not in self.peer_states:
            self.peer_states[node_id] = NodeHeartbackoffState(node_id=node_id, config=self.config)
        return self.peer_states[node_id]

    def register_heartbeat_ack(self, node_id: str, latency: float, now: Optional[float] = None) -> float:
        state = self.get_or_create_peer(node_id)
        return state.record_success(latency=latency, now=now)

    def register_heartbeat_timeout(self, node_id: str, now: Optional[float] = None) -> float:
        state = self.get_or_create_peer(node_id)
        return state.record_failure(now=now)

    def is_node_partitioned(self, node_id: str) -> bool:
        state = self.peer_states.get(node_id)
        if not state:
            return False
        return state.is_partitioned

    def get_partitioned_nodes(self) -> List[str]:
        return [nid for nid, state in self.peer_states.items() if state.is_partitioned]

    def get_peer_interval(self, node_id: str) -> float:
        state = self.get_or_create_peer(node_id)
        return state.get_current_interval()
