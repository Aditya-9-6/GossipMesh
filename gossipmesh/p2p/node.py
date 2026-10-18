import hashlib
from typing import List

from gossipmesh.node import GossipNode, GossipTopic, GossipMessage
from gossipmesh.p2p.dht import KademliaDHT, KademliaNode

class P2PGossipMeshNode(GossipNode):
    def __init__(self, node_id: str, mesh_dir: str | None = None, dht_port: int = 8468):
        super().__init__(node_id=node_id, mesh_dir=mesh_dir)
        self.dht_port = dht_port
        self.dht = KademliaDHT(local_node_id=hashlib.sha256(node_id.encode()).hexdigest())

    def register_peer(self, peer_id: str, address: str, port: int):
        peer_hex = hashlib.sha256(peer_id.encode()).hexdigest()
        node = KademliaNode(node_id=peer_hex, address=address, port=port)
        self.dht.add_node(node)

    def lookup_peer(self, peer_id: str) -> List[KademliaNode]:
        peer_hex = hashlib.sha256(peer_id.encode()).hexdigest()
        return self.dht.find_close_nodes(peer_hex)
