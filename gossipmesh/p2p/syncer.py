from gossipmesh.p2p.entropy import VectorClockEntropyCalculator


class P2PSyncer:
    def __init__(self):
        self.calculator = VectorClockEntropyCalculator()
