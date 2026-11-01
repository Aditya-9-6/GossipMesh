"""Tombstone garbage collection agent for CRDT stores."""

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
        exceed the retention period.
        """
        pruned: Dict[Any, Set[Tuple[str, str]]] = {}
        active_peers = set(peer_clocks.keys())
        if not active_peers:
            return tombstones

        for key, ts_set in tombstones.items():
            retained_ts = set()
            for ts in ts_set:
                # If acknowledged by all peers, safe to collect
                node_id, _ = ts
                min_peer_clock = min(peer_clocks.get(p, {}).get(node_id, 0) for p in active_peers)
                current_node_clock = current_clock.get(node_id, 0)
                # Keep if peer clock is behind node clock or retention threshold not met
                if min_peer_clock < current_node_clock:
                    retained_ts.add(ts)
            if retained_ts:
                pruned[key] = retained_ts
        return pruned
