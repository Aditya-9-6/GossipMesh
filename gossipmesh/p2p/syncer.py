from gossipmesh.p2p.entropy import VectorClockEntropy, VectorClockEntropyCalculator


class P2PSyncer:
    def __init__(self):
        self.calculator = VectorClockEntropyCalculator()
        self.entropy = VectorClockEntropy()
