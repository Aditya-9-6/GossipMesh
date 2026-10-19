from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self):
        self.entropy = VectorClockEntropy()

    def sync(self, node_id: str, vector_clock: dict):
        return self.entropy.compare(vector_clock)
