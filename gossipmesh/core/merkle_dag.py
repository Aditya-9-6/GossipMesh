import hashlib
import json
from typing import Dict, List, Optional, Any, Set
from gossipmesh.core.vector_clock import VectorClock

class MerkleDAGNode:
    """A single node in the Merkle DAG representing a state mutation."""
    
    def __init__(
        self, 
        node_id: str, 
        payload: Dict[str, Any], 
        parents: Optional[List[str]] = None,
        vector_clock: Optional[VectorClock] = None,
        hash_str: Optional[str] = None
    ):
        self.node_id = node_id
        self.payload = payload
        self.parents = parents or []
        self.vector_clock = vector_clock or VectorClock()
        self.hash = hash_str or self._compute_hash()

    def _compute_hash(self) -> str:
        content = {
            "node_id": self.node_id,
            "payload": self.payload,
            "parents": sorted(self.parents),
            "vector_clock": self.vector_clock.to_dict()
        }
        raw_bytes = json.dumps(content, sort_keys=True).encode('utf-8')
        return hashlib.sha256(raw_bytes).hexdigest()

    
class MerkleDAG:
    """Merkle Directed Acyclic Graph backed by Vector Clocks for mesh reconciliation."""

    def __init__(self):
        self.nodes: Dict[str, MerkleDAGNode] = {}
        self.heads: Set[str] = set()

    def add_mutation(self, node_id: str, payload: Dict[str, Any], vector_clock: VectorClock, parents: Optional[List[str]] = None) -> MerkleDAGNode:
        resolved_parents = parents if parents is not None else list(self.heads)
        dag_node = MerkleDAGNode(
            node_id=node_id,
            payload=payload,
            parents=resolved_parents,
            vector_clock=vector_clock
        )
        if dag_node.hash not in self.nodes:
            self.nodes[dag_node.hash] = dag_node
            
            # Update heads: remove parents, add new node
            for p in resolved_parents:
                if p in self.heads:
                    self.heads.remove(p)
            self.heads.add(dag_node.hash)
            
        return dag_node

    def get_node(self, hash_str: str) -> Optional[MerkleDAGNode]:
        return self.nodes.get(hash_str)

    def gc(self, finalized_hashes: Set[str]):
        """Garbage collects finalized roots to ensure bounded memory growth."""
        for h in finalized_hashes:
            if h in self.nodes and h not in self.heads:
                # Only remove non-head finalized historical nodes safely
                del self.nodes[h]
