import hashlib
from typing import Dict, List, Tuple, Any
from gossipmesh.p2p.vector_clock import VectorClock

class MerkleNode:
    """Truncated Merkle tree node for state verification and patch generation."""
    def __init__(self, key: str, value_hash: str):
        self.key = key
        self.value_hash = value_hash

class MerkleTree:
    """Simple lightweight Merkle tree for key-value state digests."""
    def __init__(self, data: Dict[str, Any]):
        self.nodes: Dict[str, MerkleNode] = {}
        for k, v in sorted(data.items()):
            v_str = str(v)
            h = hashlib.sha256(v_str.encode('utf-8')).hexdigest()
            self.nodes[k] = MerkleNode(k, h)
        
        combined = ''.join(n.value_hash for n in sorted(self.nodes.values(), key=lambda x: x.key))
        self.root_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()

    def get_diff(self, other_tree: 'MerkleTree') -> List[str]:
        keys = set(self.nodes.keys()).union(set(other_tree.nodes.keys()))
        diffs = []
        for k in keys:
            h1 = self.nodes[k].value_hash if k in self.nodes else None
            h2 = other_tree.nodes[k].value_hash if k in other_tree.nodes else None
            if h1 != h2:
                diffs.append(k)
        return diffs

class VectorClockReconciler:
    """Anti-entropy state reconciliation engine combining vector clocks with Merkle patching."""
    def __init__(self, node_id: str, state: Dict[str, Any], vector_clock: VectorClock):
        self.node_id = node_id
        self.state = state
        self.vector_clock = vector_clock

    def generate_digest(self) -> Tuple[Dict[str, int], str]:
        tree = MerkleTree(self.state)
        return self.vector_clock.to_dict(), tree.root_hash

    def reconcile(self, peer_vc_dict: Dict[str, int], peer_root_hash: str, peer_state: Dict[str, Any]) -> List[str]:
        peer_vc = VectorClock(peer_vc_dict)
        relation = self.vector_clock.compare(peer_vc)
        
        if relation == 'after':
            return []
            
        local_tree = MerkleTree(self.state)
        peer_tree = MerkleTree(peer_state)
        
        if local_tree.root_hash == peer_root_hash:
            self.vector_clock.update(peer_vc)
            return []
            
        diff_keys = local_tree.get_diff(peer_tree)
        self.vector_clock.update(peer_vc)
        return diff_keys
