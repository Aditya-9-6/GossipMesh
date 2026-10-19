from typing import Dict, Any, Tuple
from gossipmesh.p2p.entropy import VectorClockEntropyEngine


class VectorClockEntropySyncer:
    @staticmethod
    def reconcile(
        local_state: Dict[str, Any], local_clock: Dict[str, int], peer_state: Dict[str, Any], peer_clock: Dict[str, int]
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        return VectorClockEntropyEngine.reconcile_state(local_state, local_clock, peer_state, peer_clock)
