from typing import Dict, List, Optional
from gossipmesh.p2p.merkle import MerkleTree

class AntiEntropyEngine:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state_store: Dict[str, str] = {}

    def set_state(self, key: str, value: str) -> None:
        self.state_store[key] = value

    def get_state(self, key: str) -> Optional[str]:
        return self.state_store.get(key)

    def get_merkle_tree(self) -> MerkleTree:
        return MerkleTree(self.state_store)

    def get_root_hash(self) -> Optional[str]:
        return self.get_merkle_tree().get_root_hash()

    def reconcile_divergence(self, peer_store: Dict[str, str]) -> List[str]:
        local_tree = self.get_merkle_tree()
        peer_tree = MerkleTree(peer_store)
        divergent_keys: List[str] = []
        return local_tree.get_diff(peer_tree.root, local_tree.root, divergent_keys)
