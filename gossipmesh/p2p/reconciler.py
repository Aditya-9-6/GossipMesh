from typing import Dict, List, Any, Tuple
from gossipmesh.p2p.vector_clock import VectorClock

class VectorClockReconciler:
    """Reconciles peer states using vector clocks and diff digests."""
    def __init__(self, node_id: str, local_state: Dict[str, Any], vector_clock: VectorClock):
        self.node_id = node_id
        self.local_state = local_state
        self.vector_clock = vector_clock

    def generate_digest(self) -> Tuple[VectorClock, Dict[str, Any]]:
        return self.vector_clock.clone(), {k: hash(str(v)) for k, v in self.local_state.items()}

    def reconcile(self, remote_vc: VectorClock, remote_root_digest: Dict[str, Any], remote_state: Dict[str, Any]) -> List[str]:
        comparison = self.vector_clock.compare(remote_vc)
        diffs: List[str] = []
        
        if comparison == 'before' or comparison == 'concurrent':
            all_keys = set(self.local_state.keys()).union(set(remote_state.keys()))
            for k in all_keys:
                if self.local_state.get(k) != remote_state.get(k):
                    diffs.append(k)
        elif comparison == 'after':
            for k, v in remote_state.items():
                if k not in self.local_state or self.local_state[k] != v:
                    diffs.append(k)
                    
        return sorted(list(set(diffs)))
