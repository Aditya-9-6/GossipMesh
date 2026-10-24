from typing import Optional


class RTOEstimator:
    def __init__(self, alpha: float = 0.125, beta: float = 0.25) -> None:
        self.alpha = alpha
        self.beta = beta
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.rto: float = 1.0

    def update(self, rtt: float) -> None:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            assert self.rttvar is not None
            self.rttvar = (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - rtt)
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * rtt
        assert self.srtt is not None
        assert self.rttvar is not None
        self.rto = self.srtt + max(0.01, 4.0 * self.rttvar)
