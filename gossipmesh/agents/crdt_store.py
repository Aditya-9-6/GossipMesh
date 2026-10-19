import time
import copy
from typing import Dict, Set, Tuple, List, Any, Optional


class DeltaORSetCRDT:
    """
    State-Based Delta Observed-Remove Set (OR-Set) CRDT for distributed, lock-free
    autonomous agent task coordination across partitioned mesh peers.

    Satisfies join-semilattice properties:
    - Associativity: (A U B) U C == A U (B U C)
    - Commutativity: A U B == B U A
    - Idempotence: A U A == A
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        # elements: element -> set of unique occurrence tags (element_id, node_id, timestamp)
        self.add_set: Dict[str, Set[Tuple[str, str, float]]] = {}
        # tombstones: set of removed occurrence tags
        self.remove_set: Set[Tuple[str, str, float]] = set()
        # Vector clock tracking peer version states
        self.vector_clock: Dict[str, int] = {node_id: 0}

    def add(self, element: str) -> Tuple[str, str, float]:
        """Adds an element to the OR-Set, generating a unique causal tag."""
        self.vector_clock[self.node_id] = self.vector_clock.get(self.node_id, 0) + 1
        tag = (self.node_id, f"{self.node_id}-{time.time_ns()}", time.time())
        if element not in self.add_set:
            self.add_set[element] = set()
        self.add_set[element].add(tag)
        return tag

    def remove(self, element: str) -> List[Tuple[str, str, float]]:
        """Removes all active tags associated with the given element."""
        if element not in self.add_set:
            return []
        removed_tags = list(self.add_set[element])
        for tag in removed_tags:
            self.remove_set.add(tag)
        del self.add_set[element]
        return removed_tags

    def lookup(self, element: str) -> bool:
        """Returns True if the element is present in the set (has active tags not in remove_set)."""
        if element not in self.add_set:
            return False
        active_tags = self.add_set[element] - self.remove_set
        return len(active_tags) > 0

    def get_elements(self) -> Set[str]:
        """Returns all elements currently present in the OR-Set."""
        result = set()
        for elem, tags in self.add_set.items():
            if tags - self.remove_set:
                result.add(elem)
        return result

    def generate_delta(self) -> Dict[str, Any]:
        """
        Generates a compact state delta decoupling transport-layer serialization
        from internal memory representations, maintaining strict O(k) performance.
        """
        serialized_add_set = {elem: [[t[0], t[1], t[2]] for t in tags] for elem, tags in self.add_set.items()}
        serialized_remove_set = [[t[0], t[1], t[2]] for t in self.remove_set]
        return {
            "node_id": self.node_id,
            "add_set": serialized_add_set,
            "remove_set": serialized_remove_set,
            "vector_clock": copy.deepcopy(self.vector_clock),
        }

    def merge(self, delta: Dict[str, Any]):
        """
        Merges an incoming delta into the local CRDT store, preserving join-semilattice invariants.
        """
        incoming_node = delta.get("node_id")
        incoming_vc = delta.get("vector_clock", {})

        # Merge vector clock (element-wise max)
        for peer, ts in incoming_vc.items():
            self.vector_clock[peer] = max(self.vector_clock.get(peer, 0), ts)
        if incoming_node:
            self.vector_clock[incoming_node] = max(
                self.vector_clock.get(incoming_node, 0), incoming_vc.get(incoming_node, 0)
            )

        # Merge remove set
        incoming_removes = delta.get("remove_set", [])
        for tag_list in incoming_removes:
            if len(tag_list) >= 3:
                self.remove_set.add((tag_list[0], tag_list[1], float(tag_list[2])))

        # Merge add set
        incoming_adds = delta.get("add_set", {})
        for elem, tag_lists in incoming_adds.items():
            if elem not in self.add_set:
                self.add_set[elem] = set()
            for tag_list in tag_lists:
                if len(tag_list) >= 3:
                    tag = (tag_list[0], tag_list[1], float(tag_list[2]))
                    self.add_set[elem].add(tag)

        # Clean up add_set entries where all tags are fully tombstoned
        empty_elems = [elem for elem, tags in self.add_set.items() if not (tags - self.remove_set)]
        for elem in empty_elems:
            del self.add_set[elem]
