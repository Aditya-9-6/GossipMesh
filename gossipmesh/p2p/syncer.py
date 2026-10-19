from typing import List, Dict, Any
from gossipmesh.p2p.node import GossipNode, GossipMessage


class MeshSyncer:
    """Coordinates anti-entropy synchronization across peer nodes."""

    def __init__(self, node: GossipNode):
        self.node = node

    def sync_mesh(self) -> List[GossipMessage]:
        """Trigger node synchronization and return new messages discovered."""
        return self.node.sync()
