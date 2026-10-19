from typing import Any, Dict, Optional
from gossipmesh.p2p.entropy import VectorClock


class VectorClockSyncer:
    """Syncs state between peers using VectorClocks."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.clock = VectorClock(node_id)

    def prepare_sync(self) -> Dict[str, int]:
        return self.clock.get_state()

    def reconcile(self, remote_state: Dict[str, int]) -> bool:
        remote_clock = VectorClock.from_state(remote_state)
        return self.clock.merge(remote_clock)
