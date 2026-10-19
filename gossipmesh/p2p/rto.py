from typing import Optional


class RTOEstimator:
    def __init__(self, alpha: float = 0.125, beta: float = 0.25):
        self.alpha = alpha
        self.beta = beta
        self.srto: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.rto: float = 1.0

    def update(self, rtt: float) -> float:
        if self.srto is None:
            self.srto = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = (1 - self.beta) * self.rttvar + self.beta * abs(self.srto - rtt)
            self.srto = (1 - self.alpha) * self.srto + self.alpha * rtt

        assert self.srto is not None
        assert self.rttvar is not None
        self.rto = self.srto + max(0.01, 4.0 * self.rttvar)
        return self.rto
