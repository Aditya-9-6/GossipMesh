import threading
from typing import Any, Dict, Set, Tuple


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
            pruned_tombstones: Dict[Any, Set[Tuple[str, str]]] = {}

            # Calculate stable tick across peers per node
            node_stable_ticks: Dict[str, int] = {}
            if peer_clocks:
                for node_id in current_clock.keys():
                    peer_ticks = [clock.get(node_id, 0) for clock in peer_clocks.values()]
                    if peer_ticks:
                        node_stable_ticks[node_id] = min(peer_ticks)
                    else:
                        node_stable_ticks[node_id] = 0
            else:
                for node_id in current_clock.keys():
                    node_stable_ticks[node_id] = current_clock.get(node_id, 0)

            for elem, tags in tombstones.items():
                retained_tags: Set[Tuple[str, str]] = set()
                for tag_id, tag_node in tags:
                    node_stable_tick = node_stable_ticks.get(tag_node, 0)
                    try:
                        counter = int(tag_id.split("-")[-1])
                    except (ValueError, IndexError):
                        counter = 0

                    if counter > node_stable_tick:
                        retained_tags.add((tag_id, tag_node))

                if retained_tags:
                    pruned_tombstones[elem] = retained_tags

            return pruned_tombstones
