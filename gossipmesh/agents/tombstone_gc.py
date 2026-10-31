import threading
from typing import Dict, Set, Tuple, Any


class TombstoneGarbageCollector:
    def __init__(self):
        self._lock = threading.Lock()

    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        current_clock: Dict[str, int],
        peer_clocks: Dict[str, Dict[str, int]],
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        """
        Prunes tombstones that have been acknowledged by all active peers or whose node ticks
        exceed the stability threshold.
        """
        with self._lock:
            if not tombstones:
                return {}

            # Compute stability threshold across peer vector clocks
            all_node_ids = set(current_clock.keys())
            for p_clock in peer_clocks.values():
                all_node_ids.update(p_clock.keys())

            # For each node, find the minimum clock tick seen across all active peers
            node_stable_tick = {}
            for node_id in all_node_ids:
                ticks = [current_clock.get(node_id, 0)]
                for p_clock in peer_clocks.values():
                    ticks.append(p_clock.get(node_id, 0))
                node_stable_tick[node_id] = min(ticks)

            pruned_tombstones = {}
            for elem, tags in tombstones.items():
                retained_tags = set()
                for tag_id, tag_node in tags:
                    # Extract counter from tag_id (format: node_id-counter)
                    try:
                        counter = int(tag_id.split("-")[-1])
                    except (ValueError, IndexError):
                        counter = 0

                    stable_tick = node_stable_tick.get(tag_node, 0)
                    if counter > stable_tick:
                        retained_tags.add((tag_id, tag_node))

                if retained_tags:
                    pruned_tombstones[elem] = retained_tags

            return pruned_tombstones
