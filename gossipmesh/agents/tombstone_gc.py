import threading
from typing import Any, Dict, Set, Tuple
from gossipmesh.core.clocks import VectorClock


class TombstoneGarbageCollector:
    def __init__(self):
        pass

    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        peer_clocks: Dict[str, VectorClock],
        current_clock: VectorClock,
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        return tombstones
