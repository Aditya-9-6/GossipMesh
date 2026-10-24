from gossipmesh.p2p.entropy import VectorClockEntropy


class Syncer:
    def __init__(self):
        self.entropy = VectorClockEntropy()
