from typing import Dict, Set, Tuple, Any


class TombstoneGarbageCollector:
    def __init__(self, ttl_ticks: int = 100):
        self.ttl_ticks = ttl_ticks

    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        current_clock: Dict[str, int],
        peer_clocks: Dict[str, Dict[str, int]],
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        """
        Prunes tombstones that have been acknowledged by all active peers or whose node ticks
        exceed the TTL threshold.
        """
        active_keys = set(current_clock.keys())
        pruned_tombstones: Dict[Any, Set[Tuple[str, str]]] = {}

        for key, records in tombstones.items():
            retained_records: Set[Tuple[str, str]] = set()
            for record in records:
                node_id, timestamp_str = record
                try:
                    timestamp = int(timestamp_str)
                except ValueError:
                    retained_records.add(record)
                    continue

                # Check if TTL exceeded
                current_tick = current_clock.get(node_id, 0)
                if current_tick - timestamp > self.ttl_ticks:
                    continue  # Pruned due to TTL

                # Check if acknowledged by all peers
                acknowledged_by_all = True
                for peer_id, p_clock in peer_clocks.items():
                    if p_clock.get(node_id, 0) < timestamp:
                        acknowledged_by_all = False
                        break

                if not acknowledged_by_all:
                    retained_records.add(record)

            if retained_records:
                pruned_tombstones[key] = retained_records

        return pruned_tombstones
