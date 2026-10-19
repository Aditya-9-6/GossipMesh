from typing import Optional


class AdaptiveRTO:
    """Jacobson/Karels RTO Calculator for P2P Gossip Links."""

    def __init__(self, initial_rto: float = 1.0, alpha: float = 0.125, beta: float = 0.25):
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.rto: float = initial_rto
        self.alpha = alpha
        self.beta = beta

    def update(self, measured_rtt: float) -> float:
        if self.srtt is None:
            self.srtt = measured_rtt
            self.rttvar = measured_rtt / 2.0
        else:
            assert self.srtt is not None
            assert self.rttvar is not None
            self.rttvar = (1.0 - self.beta) * self.rttvar + self.beta * abs(self.srtt - measured_rtt)
            self.srtt = (1.0 - self.alpha) * self.srtt + self.alpha * measured_rtt

        assert self.srtt is not None
        assert self.rttvar is not None
        self.rto = self.srtt + max(0.01, 4.0 * self.rttvar)
        return self.rto
