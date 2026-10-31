import threading
from typing import Dict, Set, Optional, Any, Tuple
from gossipmesh.agents.crdt_store import DeltaORSetStore
from gossipmesh.core.clocks import VectorClock


class AgentTaskAllocator:
    """
    Decentralized Task Allocator coordinating concurrent multi-agent task assignments
    across mesh peers using Delta-State OR-Set CRDTs.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.store = DeltaORSetStore(node_id=node_id)
        self.vector_clock = VectorClock(node_id=node_id)
        self._lock = threading.Lock()

    def claim_task(self, task_id: str, agent_id: str) -> Tuple[str, Set[Tuple[str, str]]]:
        """
        Claims a task for a given agent. Returns task assignment and generated delta tags.
        """
        with self._lock:
            self.vector_clock.increment()
            assignment = f"{task_id}:{agent_id}"
            _, delta_tags = self.store.add(assignment)
            return assignment, delta_tags

    def release_task(self, task_id: str, agent_id: str) -> Tuple[str, Set[Tuple[str, str]]]:
        """
        Releases/unclaims a task for a given agent.
        """
        with self._lock:
            self.vector_clock.increment()
            assignment = f"{task_id}:{agent_id}"
            _, removed_tags = self.store.remove(assignment)
            return assignment, removed_tags

    def get_active_tasks(self) -> Set[str]:
        """Returns all currently active task assignments across the mesh."""
        return self.store.read()

    def merge_peer_sync(
        self,
        peer_node_id: str,
        peer_clock: Dict[str, int],
        delta: Dict[str, Set[Tuple[str, str]]],
        tombstones: Optional[Dict[str, Set[Tuple[str, str]]]] = None,
    ) -> None:
        """
        Synchronizes state with a remote peer using incoming delta and vector clock update.
        """
        with self._lock:
            self.vector_clock.update(peer_clock)
            self.store.merge_delta(delta, tombstones)
