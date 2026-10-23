from typing import Optional
import time


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0, alpha: float = 0.125, beta: float = 0.25):
        self.rto: Optional[float] = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.alpha = alpha
        self.beta = beta

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

        if self.srtt is not None and self.rttvar is not None:
            self.rto = self.srtt + max(0.01, 4.0 * self.rttvar)

    def get_rto(self) -> float:
        return self.rto if self.rto is not None else 1.0
