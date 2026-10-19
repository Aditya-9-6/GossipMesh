from gossipmesh.p2p.entropy import VectorClockEntropy


class PeerSyncer:
    def __init__(self):
        self.entropy = VectorClockEntropy()

    def sync(self, peer_id: str, vector_clock: dict) -> dict:
        return self.entropy.reconcile(vector_clock)
