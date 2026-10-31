"""
Tombstone Garbage Collector for GossipMesh CRDT states.
"""

from typing import Any, Dict, Set, Tuple


class TombstoneGarbageCollector:
    def __init__(self, ttl_ticks: int = 100) -> None:
        self.ttl_ticks = ttl_ticks

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
        pruned: Dict[Any, Set[Tuple[str, str]]] = {}
        min_peer_clock = {}

        for peer, clock_map in peer_clocks.items():
            for node, tick in clock_map.items():
                if node not in min_peer_clock or tick < min_peer_clock[node]:
                    min_peer_clock[node] = tick

        for key, entry_set in tombstones.items():
            active_entries: Set[Tuple[str, str]] = set()
            for entry in entry_set:
                node = entry[0]
                node_tick = current_clock.get(node, 0)
                acknowledged_tick = min_peer_clock.get(node, 0)

                # If acknowledged by all peers or exceeds TTL, prune it
                if node_tick - acknowledged_tick < self.ttl_ticks:
                    active_entries.add(entry)

            if active_entries:
                pruned[key] = active_entries

        return pruned
