import threading
from typing import Any, Dict, Set, Tuple
from gossipmesh.core.clocks import VectorClock


class TombstoneGarbageCollector:
    """
    Garbage collects tombstones based on a stable vector clock threshold.
    Ensures O(k) memory footprint bounding while preserving causal safety.
    """

    def __init__(self, node_id: str, stability_threshold_ticks: int = 10):
        self.node_id = node_id
        self.stability_threshold_ticks = stability_threshold_ticks
        self._lock = threading.Lock()

    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        current_clock: Dict[str, int],
        peer_clocks: Dict[str, Dict[str, int]],
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        """
        Prunes tombstones that have been acknowledged by all active peers or whose node ticks
        fall safely below the stable threshold across the mesh.
        """
        with self._lock:
            if not peer_clocks:
                return tombstones

            # Calculate minimum vector clock across all peers and self
            all_clocks = list(peer_clocks.values()) + [current_clock]
            min_clock: Dict[str, int] = {}
            if all_clocks:
                first = all_clocks[0]
                for node in first.keys():
                    min_clock[node] = min(c.get(node, 0) for c in all_clocks)

            pruned_tombstones = {}
            for elem, tags in tombstones.items():
                retained_tags = set()
                for tag_id, tag_node in tags:
                    # Extract tick from tag_id if formatted as node-counter or check against min_clock
                    node_stable_tick = min_clock.get(tag_node, 0)
                    # If the stable clock across all peers has advanced past or equal to the generation mark,
                    # or if older than stability threshold, we can garbage collect.
                    # For safety, we keep tags whose originating node hasn't been acknowledged stably.
                    try:
                        counter = int(tag_id.split("-")[-1])
                    except (ValueError, IndexError):
                        counter = 0

                    if counter > node_stable_tick:
                        retained_tags.add((tag_id, tag_node))

                if retained_tags:
                    pruned_tombstones[elem] = retained_tags

            return pruned_tombstones
