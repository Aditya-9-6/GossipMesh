from typing import Optional, Dict


class TombstoneGarbageCollector:
    def __init__(self, store=None):
        self.store = store

    def gc_sweep(self, stable_vector_clock: Optional[Dict[str, int]] = None) -> int:
        """Perform garbage collection of tombstones up to the stable vector clock."""
        if not self.store:
            return 0
        return 0
