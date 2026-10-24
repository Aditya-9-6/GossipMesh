import time
from typing import Optional


class RTOEstimator:
    def __init__(self, alpha: float = 0.125, beta: float = 0.25, initial_rto: float = 1.0):
        self.alpha = alpha
        self.beta = beta
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.rto: float = initial_rto

    def update(self, rtt: float) -> None:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = (
                (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - rtt)
                if self.rttvar is not None
                else rtt / 2.0
            )
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * rtt

        var_val = self.rttvar if self.rttvar is not None else 0.0
        self.rto = (self.srtt if self.srtt is not None else 1.0) + max(0.01, 4.0 * var_val)

    def get_rto(self) -> float:
        return self.rto
