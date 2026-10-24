import time
from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0):
        self.rto = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None

    def update(self, rtt: float) -> float:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            alpha = 0.125
            beta = 0.25
            self.rttvar = (1 - beta) * (self.rttvar if self.rttvar is not None else 0.0) + beta * abs(self.srtt - rtt)
            self.srtt = (1 - alpha) * self.srtt + alpha * rtt

        assert self.srtt is not None
        assert self.rttvar is not None
        self.rto = self.srtt + max(0.01, 4.0 * self.rttvar)
        return self.rto

    def get_rto(self) -> float:
        return self.rto
