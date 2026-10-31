import threading
from typing import Dict, Set, Any, Tuple, Optional


class DeltaORSetStore:
    """
    Delta-state Observed-Remove Set (OR-Set) CRDT for decentralized agent task allocation.
    Supports concurrent additions and removals with join-semilattice associativity,
    commutativity, and idempotence.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        # elements: element -> set of unique tag tuples (tag_id, node_id)
        self._elements: Dict[Any, Set[Tuple[str, str]]] = {}
        # tombstones: element -> set of unique tag tuples (tag_id, node_id) that were removed
        self._tombstones: Dict[Any, Set[Tuple[str, str]]] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def _generate_tag(self) -> Tuple[str, str]:
        self._counter += 1
        return (f"{self.node_id}-{self._counter}", self.node_id)

    def add(self, element: Any) -> Tuple[Any, Set[Tuple[str, str]]]:
        """
        Adds an element by generating a unique tag. Returns the element and the delta generated.
        """
        with self._lock:
            tag = self._generate_tag()
            if element not in self._elements:
                self._elements[element] = set()
            self._elements[element].add(tag)
            return element, {tag}

    def remove(self, element: Any) -> Tuple[Any, Set[Tuple[str, str]]]:
        """
        Removes an element by moving all its current active tags to tombstones.
        Returns the element and the removed tags delta.
        """
        with self._lock:
            if element not in self._elements:
                return element, set()
            removed_tags = set(self._elements[element])
            if element not in self._tombstones:
                self._tombstones[element] = set()
            self._tombstones[element].update(removed_tags)
            del self._elements[element]
            return element, removed_tags

    def read(self) -> Set[Any]:
        """Returns the set of active elements present in the OR-Set."""
        with self._lock:
            return set(self._elements.keys())

    def merge_delta(
        self, delta: Dict[str, Set[Tuple[str, str]]], tombstones: Optional[Dict[str, Set[Tuple[str, str]]]] = None
    ) -> None:
        """
        Merges incoming delta and tombstones satisfying join-semilattice properties.
        delta format: {element: set_of_tags}
        tombstones format: {element: set_of_removed_tags}
        """
        with self._lock:
            tombstones = tombstones or {}

            # First, update global tombstones with incoming tombstones
            for elem, incoming_t_tags in tombstones.items():
                if elem not in self._tombstones:
                    self._tombstones[elem] = set()
                self._tombstones[elem].update(incoming_t_tags)
                # If present in active elements, remove any tags that are now tombstoned
                if elem in self._elements:
                    self._elements[elem] -= self._tombstones[elem]
                    if not self._elements[elem]:
                        del self._elements[elem]

            # Next, merge incoming active element tags
            for elem, incoming_tags in delta.items():
                # Filter out any tags already present in tombstones
                current_tombstones = self._tombstones.get(elem, set())
                valid_new_tags = incoming_tags - current_tombstones

                if valid_new_tags:
                    if elem not in self._elements:
                        self._elements[elem] = set()
                    self._elements[elem].update(valid_new_tags)

    def get_full_state(self) -> Tuple[Dict[str, Set[Tuple[str, str]]], Dict[str, Set[Tuple[str, str]]]]:
        """Returns deep copy of current elements and tombstones for full state sync."""
        with self._lock:
            return ({k: set(v) for k, v in self._elements.items()}, {k: set(v) for k, v in self._tombstones.items()})
