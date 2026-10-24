from gossipmesh.p2p.entropy import VectorClockEntropy


class Syncer:
    def __init__(self) -> None:
        self.entropy = VectorClockEntropy()


class P2PSyncer(Syncer):
    pass
