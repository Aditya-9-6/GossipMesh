"""
Tombstone Garbage Collector Agent for Distributed Delta-OR Sets.
"""

import logging
import threading
from typing import Any, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TombstoneGarbageCollector:
    """
    Manages garbage collection of old tombstones based on vector clocks and stability thresholds.
    """

    def __init__(self, node_id: str, stability_window: int = 10):
        self.node_id = node_id
        self.stability_window = stability_window
        self._lock = threading.Lock()

    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        current_clock: Dict[str, int],
        peer_clocks: Dict[str, Dict[str, int]],
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        """
        Prunes tombstones that have been acknowledged by all active peers or whose node ticks
        exceed the stability window.
        """
        with self._lock:
            pruned_tombstones: Dict[Any, Set[Tuple[str, str]]] = {}

            # Determine minimum stable tick across all peers
            node_stable_tick = current_clock.get(self.node_id, 0) - self.stability_window
            for peer_id, p_clock in peer_clocks.items():
                peer_tick = p_clock.get(self.node_id, 0)
                if peer_tick < node_stable_tick:
                    node_stable_tick = peer_tick

            for elem, tags in tombstones.items():
                retained_tags = set()
                for tag_id, tag_node in tags:
                    # Parse tag node tick or fallback to checking against stable tick
                    # If tag counter is newer than node_stable_tick, we keep it,
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
