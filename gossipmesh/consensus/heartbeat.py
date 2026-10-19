import time
import asyncio
from typing import Dict, Callable, Optional, Any
from gossipmesh.consensus.backoff import AdaptiveBackoffController


class HeartbeatManager:
    """Manages node heartbeats with decentralized adaptive backoff."""

    def __init__(
        self,
        node_id: str,
        ping_callback: Callable[[str], float],
        controller: Optional[AdaptiveBackoffController] = None,
    ):
        self.node_id = node_id
        self.ping_callback = ping_callback
        self.controller = controller or AdaptiveBackoffController()
        self._active_peers: Dict[str, float] = {}

    def register_peer(self, peer_id: str):
        self._active_peers[peer_id] = time.time()

    def unregister_peer(self, peer_id: str):
        self._active_peers.pop(peer_id, None)

    async def pulse(self, peer_id: str) -> bool:
        start_time = time.time()
        try:
            success = await asyncio.to_thread(self.ping_callback, peer_id)
            latency = time.time() - start_time
            if success:
                self.controller.record_success(peer_id, latency)
                self._active_peers[peer_id] = time.time()
                return True
            else:
                self.controller.record_failure(peer_id)
                return False
        except Exception:
            self.controller.record_failure(peer_id)
            return False

    def get_next_interval(self, peer_id: str) -> float:
        return self.controller.get_backoff_interval(peer_id)
