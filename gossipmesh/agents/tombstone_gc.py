from typing import Dict, Set, Tuple, Any


class TombstoneGarbageCollector:
    def __init__(self, ttl_ticks: int = 100):
        self.ttl_ticks = ttl_ticks

    def gc_tombstones(
        self,
        tombstones: Dict[Any, Set[Tuple[str, str]]],
        current_clock: Dict[str, int],
        peer_clocks: Dict[str, Dict[str, int]],
    ) -> Dict[Any, Set[Tuple[str, str]]]:
        pruned: Dict[Any, Set[Tuple[str, str]]] = {}
        for key, items in tombstones.items():
            active_items = set()
            for item in items:
                node_id, tick_str = item
                try:
                    tick_val = int(tick_str)
                except ValueError:
                    active_items.add(item)
                    continue

                acknowledged_everywhere = True
                if peer_clocks:
                    for peer, p_clock in peer_clocks.items():
                        if p_clock.get(node_id, 0) < tick_val:
                            acknowledged_everywhere = False
                            break
                else:
                    acknowledged_everywhere = False

                if not acknowledged_everywhere:
                    active_items.add(item)
            if active_items:
                pruned[key] = active_items
        return pruned
