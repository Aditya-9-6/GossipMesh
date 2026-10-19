from gossipmesh.p2p.entropy import VectorClockEntropy


class Syncer:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.entropy = VectorClockEntropy(node_id)
