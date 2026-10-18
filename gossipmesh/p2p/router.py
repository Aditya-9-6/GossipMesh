from typing import Dict, Any, List, Optional
from gossipmesh.p2p.plumtree import PlumTreeMesh

class P2PRouter:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.mesh = PlumTreeMesh(node_id)

    def register_peer(self, peer_id: str, eager: bool = True) -> None:
        if eager:
            self.mesh.add_eager_peer(peer_id)
        else:
            self.mesh.add_lazy_peer(peer_id)

    def unregister_peer(self, peer_id: str) -> None:
        self.mesh.remove_peer(peer_id)

    def route_message(self, message_id: str, payload: Any, from_peer: str) -> Dict[str, Any]:
        is_duplicate = self.mesh.handle_message(message_id, payload, from_peer)
        
        # Determine forwarding targets
        eager_targets = self.mesh.get_eager_peers()
        if from_peer in eager_targets:
            eager_targets.remove(from_peer)

        lazy_targets = self.mesh.get_lazy_peers()
        if from_peer in lazy_targets:
            lazy_targets.remove(from_peer)

        return {
            "is_duplicate": is_duplicate,
            "forward_eager": eager_targets,
            "forward_lazy": lazy_targets,
        }
