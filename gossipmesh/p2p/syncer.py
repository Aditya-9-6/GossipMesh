from gossipmesh.p2p.entropy import VectorClockEntropy


class P2PSyncer:
    def __init__(self):
        self.entropy = VectorClockEntropy()
