import time
from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0) -> None:
        self.rto = initial_rto
        self.srtt: float | None = None
        self.rttvar: float | None = None

    def update(self, rtt: float) -> None:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            alpha = 0.125
            beta = 0.25
            assert self.rttvar is not None
            self.rttvar = (1 - beta) * self.rttvar + beta * abs(self.srtt - rtt)
            self.srtt = (1 - alpha) * self.srtt + alpha * rtt

        self.rto = self.srtt + max(0.01, 4.0 * (self.rttvar or 0.0))

    def get_rto(self) -> float:
        return self.rto


def calculate_rto(srtt: Optional[float], rttvar: float, rtt: float) -> float:
    base_srtt = srtt if srtt is not None else rtt
    return base_srtt + 4.0 * rttvar
