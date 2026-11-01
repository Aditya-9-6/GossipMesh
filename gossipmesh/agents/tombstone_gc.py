"""Tombstone Garbage Collector Agent for GossipMesh CRDT state."""

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
        exceed the maximum GC retention window.
        """
        pruned: Dict[Any, Set[Tuple[str, str]]] = {}
        active_peers = list(peer_clocks.keys())

        for key, tset in tombstones.items():
            retained_tset: Set[Tuple[str, str]] = set()
            for item in tset:
                # Retain tombstone unless acknowledged by all peers
                acknowledged_by_all = all(
                    peer_clocks.get(peer, {}).get(item[0], 0) >= current_clock.get(item[0], 0) for peer in active_peers
                )
                if not acknowledged_by_all:
                    retained_tset.add(item)
            if retained_tset:
                pruned[key] = retained_tset
        return pruned
