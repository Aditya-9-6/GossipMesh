from gossipmesh.p2p.entropy import VectorClockEntropy, AntiEntropyEntropy


class MeshSyncer:
    def __init__(self):
        self.entropy_calculator = VectorClockEntropy()
        self.anti_entropy = AntiEntropyEntropy()

    def sync(self):
        pass
