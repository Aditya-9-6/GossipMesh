from gossipmesh.p2p.entropy import AntiEntropyEngine


class AntiEntropySyncer:
    def __init__(self) -> None:
        self.entropy = AntiEntropyEngine()
