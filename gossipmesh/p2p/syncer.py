from gossipmesh.p2p.entropy import VectorClockEntropy


class PeerSyncer:
    def __init__(self) -> None:
        self.entropy = VectorClockEntropy()
