import time
from typing import Dict, Any, Set, Tuple
from gossipmesh.agents.crdt_store import DeltaORSetCRDT

class TombstoneGarbageCollector:
    """
    Enforces tombstone garbage collection bounded by a stable vector clock threshold
    and TTL, maintaining strict O(k) delta merge performance and preventing memory leaks.
    """
    def __init__(self, crdt_store: DeltaORSetCRDT, ttl_seconds: float = 86400.0):
        self.crdt_store = crdt_store
        self.ttl_seconds = ttl_seconds

    def gc_sweep(self, stable_vector_clock: Optional[Dict[str, int]] = None) -> int:
        """
        Sweeps and purges tombstones that are older than the TTL or acknowledged
        by all stable vector clock peer thresholds.
        Returns the number of purged tombstones.
        """
        current_time = time.time()
        purged_count = 0
        retained_remove_set: Set[Tuple[str, str, float]] = set()

        for tag in self.crdt_store.remove_set:
            _, _, timestamp = tag
            age = current_time - timestamp
            
            # Check if expired by TTL
            is_expired_ttl = age > self.ttl_seconds
            
            # Check if acknowledged by stable vector clock
            is_acknowledged = False
            if stable_vector_clock:
                node, _, tag_ts = tag
                peer_stable_ts = stable_vector_clock.get(node, 0)
                if tag_ts <= peer_stable_ts:
                    is_acknowledged = True

            if is_expired_ttl or is_acknowledged:
                purged_count += 1
            else:
                retained_remove_set.add(tag)

        self.crdt_store.remove_set = retained_remove_set
        return purged_count
