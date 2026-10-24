from typing import Optional
import time


class RTOEstimator:
    def __init__(
        self,
        initial_rto: float = 1.0,
        alpha: float = 0.125,
        beta: float = 0.25,
        rttvar: Optional[float] = None,
        srtt: Optional[float] = None,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.rto = initial_rto
        self.rttvar = rttvar if rttvar is not None else (None if srtt is None else 0.0)
        self.srtt = srtt

    def update(self, rtt: float) -> float:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            assert self.rttvar is not None
            self.rttvar = (
                (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - rtt)
                if self.rttvar is not None
                else rtt / 2.0
            )
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * rtt

        assert self.srtt is not None
        assert self.rttvar is not None
        self.rto = self.srtt + max(0.01, 4.0 * self.rttvar)
        return self.rto

    def calculate(self, sample: float) -> float:
        return sample * 1.5

    def get_rto(self) -> float:
        return self.rto if self.rto is not None else 1.0
