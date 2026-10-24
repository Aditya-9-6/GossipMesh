from __future__ import annotations
import time


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0, alpha: float = 0.125, beta: float = 0.25):
        self.rto = initial_rto
        self.srtt: float | None = None
        self.rttvar: float | None = None
        self.alpha = alpha
        self.beta = beta

    def update(self, rtt: float) -> float:
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

        rttvar_val = self.rttvar if self.rttvar is not None else 0.0
        srtt_val = self.srtt if self.srtt is not None else rtt
        self.rto = srtt_val + max(0.01, 4.0 * rttvar_val)
        return self.rto

    def get_rto(self) -> float:
        return self.rto
