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

            # Calculate stable vector clock across active peers
            active_peers = list(peer_clocks.keys())
            if not active_peers:
                return {k: set(v) for k, v in tombstones.items()}

            node_stable_tick = {}
            for node_id in current_clock:
                peer_ticks = [peer_clocks[p].get(node_id, 0) for p in active_peers]
                node_stable_tick[node_id] = min([current_clock.get(node_id, 0)] + peer_ticks)

            for elem, tags in tombstones.items():
                retained_tags = set()
                for tag_id, tag_node in tags:
                    # Extract counter from tag_id if formatted as node-counter or similar,
                    # or if older than stability threshold, we can garbage collect.
                    # For safety, we keep tags whose originating node hasn't been acknowledged stably.
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
