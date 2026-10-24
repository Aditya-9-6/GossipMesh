from gossipmesh.p2p.node import P2PNode, GossipNode, GossipMessage, GossipTopic


class RTOEstimator:
    def __init__(self) -> None:
        self.rto = 1.0

    def update(self, rtt: float) -> None:
        self.rto = 0.8 * self.rto + 0.2 * rtt


__all__ = [["P2PNode", "GossipNode", "GossipMessage", "GossipTopic", "RTOEstimator"]]
