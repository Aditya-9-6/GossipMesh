import time
from typing import Optional


class AdaptiveRTO:
    def __init__(self, initial_rto: float = 1.0, alpha: float = 0.125, beta: float = 0.25):
        self.rto = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.alpha = alpha
        self.beta = beta

    def update(self, measured_rtt: float):
        if self.srtt is None:
            self.srtt = measured_rtt
            self.rttvar = measured_rtt / 2.0
        else:
            self.rttvar = (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - measured_rtt)
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * measured_rtt

        rttvar_val = self.rttvar if self.rttvar is not None else 0.0
        srtt_val = self.srtt if self.srtt is not None else measured_rtt
        self.rto = srtt_val + max(0.01, 4.0 * rttvar_val)

    def get_rto(self) -> float:
        return self.rto
