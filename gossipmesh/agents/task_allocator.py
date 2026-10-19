from typing import Dict, List, Set, Any, Optional
from gossipmesh.agents.crdt_store import DeltaORSetCRDT

class TaskAllocator:
    """
    Coordinates autonomous agent task claims and assignments across partitioned mesh peers
    using the DeltaORSetCRDT without central locks.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.crdt = DeltaORSetCRDT(node_id)
        self.task_metadata: Dict[str, Dict[str, Any]] = {}

    def claim_task(self, task_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Claims a task for the current node agent."""
        tag = self.crdt.add(task_id)
        if metadata:
            self.task_metadata[task_id] = metadata
        return {
            "task_id": task_id,
            "node_id": self.node_id,
            "tag": tag,
            "delta": self.crdt.generate_delta()
        }

    def release_task(self, task_id: str) -> Dict[str, Any]:
        """Releases a claimed task by removing it from the active OR-Set."""
        self.crdt.remove(task_id)
        if task_id in self.task_metadata:
            del self.task_metadata[task_id]
        return {
            "task_id": task_id,
            "node_id": self.node_id,
            "delta": self.crdt.generate_delta()
        }

    def get_active_tasks(self) -> Set[str]:
        """Returns all currently active tasks claimed across the mesh."""
        return self.crdt.get_elements()

    def is_task_claimed(self, task_id: str) -> bool:
        """Checks if a specific task is currently claimed."""
        return self.crdt.lookup(task_id)

    def receive_delta(self, delta: Dict[str, Any]):
        """Receives and merges a delta from a peer node."""
        self.crdt.merge(delta)
