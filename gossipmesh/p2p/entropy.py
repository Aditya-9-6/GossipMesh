from typing import Dict, List, Optional
from gossipmesh.p2p.merkle import MerkleTree


class AntiEntropyManager:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state_store: Dict[str, str] = {}

    def set_state(self, key: str, value: str) -> None:
        self.state_store[key] = value

    def get_state(self, key: str) -> Optional[str]:
        return self.state_store.get(key)

    def get_merkle_tree(self) -> MerkleTree:
        return MerkleTree(self.state_store)

    def reconcile_state(self, peer_id: str, peer_tree: MerkleTree) -> List[str]:
        local_tree = self.get_merkle_tree()
        if local_tree.get_root_hash() == peer_tree.get_root_hash():
            return []
        return local_tree.find_divergent_keys(peer_tree.root)
