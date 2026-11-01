"""Garbage collection engine for tombstoned state records."""

from typing import Dict, Set, Tuple, Any


class TombstoneGarbageCollector:
    """Prunes acknowledged or expired tombstones."""

    def __init__(self, ttl_ticks: int = 1000) -> None:
        self.ttl_ticks = ttl_ticks

    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        current_clock: Dict[str, int],
        peer_clocks: Dict[str, Dict[str, int]],
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        """
        Prunes tombstones that have been acknowledged by all active peers or whose node ticks
        have exceeded the TTL threshold.
        """
        pruned: Dict[Any, Set[Tuple[str, str]]] = {}
        for key, records in tombstones.items():
            retained_records = set()
            for record in records:
                node_id, timestamp_str = record
                # Retain if not acknowledged by all peers and within TTL
                if node_id in current_clock:
                    node_time = current_clock[node_id]
                    # Check if acknowledged by all peers
                    acked_by_all = all(peer_clock.get(node_id, 0) >= node_time for peer_clock in peer_clocks.values())
                    if not acked_by_all:
                        retained_records.add(record)
            if retained_records:
                pruned[key] = retained_records
        return pruned
