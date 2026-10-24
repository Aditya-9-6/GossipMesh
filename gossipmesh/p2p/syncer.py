from gossipmesh.p2p.entropy import StateEntropy


class Syncer:
    def __init__(self) -> None:
        self.entropy = StateEntropy()
