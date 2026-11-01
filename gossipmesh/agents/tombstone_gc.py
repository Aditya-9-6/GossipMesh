from typing import Dict, Set, Tuple, Any


class TombstoneGarbageCollector:
    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        current_clock: Dict[str, int],
        peer_clocks: Dict[str, Dict[str, int]],
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        """
        Prunes tombstones that have been acknowledged by all active peers or whose node ticks
        exceed the retention window.
        """
        active_clocks = list(peer_clocks.values()) + [current_clock]
        pruned: Dict[Any, Set[Tuple[str, str]]] = {}

        for key, ts_set in tombstones.items():
            retained_ts: Set[Tuple[str, str]] = set()
            for node_id, ts_val in ts_set:
                # If all active peers have vector clocks >= this timestamp, safe to GC
                acknowledged_by_all = all(clock.get(node_id, 0) >= int(ts_val) for clock in active_clocks if clock)
                if not acknowledged_by_all:
                    retained_ts.add((node_id, ts_val))
            if retained_ts:
                pruned[key] = retained_ts
        return pruned
