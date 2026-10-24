import time
from typing import Optional


class RTOEstimator:
    def __init__(self, rttvar: Optional[float] = None, srtt: Optional[float] = None, initial_rto: float = 1.0):
        self.rto = initial_rto
        self.rttvar = rttvar if rttvar is not None else 0.0
        self.srtt = srtt if srtt is not None else 0.0

    def update(self, rtt: float):
        if self.srtt == 0.0 and self.rttvar == 0.0 and self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            alpha = 0.125
            beta = 0.25
            self.rttvar = (1 - beta) * self.rttvar + beta * abs(self.srtt - rtt)
            self.srtt = (1 - alpha) * self.srtt + alpha * rtt

        self.rto = self.srtt + max(0.01, 4.0 * (self.rttvar or 0.0))

    def calculate(self, sample: float) -> float:
        return sample * 1.5

    def get_rto(self) -> float:
        return self.rto
