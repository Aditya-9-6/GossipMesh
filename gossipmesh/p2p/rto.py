from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0, alpha: float = 0.125, beta: float = 0.25):
        self.rto: float = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.alpha = alpha
        self.beta = beta

    def update(self, rtt: float) -> float:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            rttvar_val = self.rttvar if self.rttvar is not None else 0.0
            srtt_val = self.srtt if self.srtt is not None else 0.0
            self.rttvar = (1 - self.beta) * rttvar_val + self.beta * abs(srtt_val - rtt)
            self.srtt = (1 - self.alpha) * srtt_val + self.alpha * rtt

        rttvar_val = self.rttvar if self.rttvar is not None else 0.0
        srtt_val = self.srtt if self.srtt is not None else 0.0
        self.rto = srtt_val + max(0.01, 4.0 * rttvar_val)
        return self.rto

    def get_rto(self) -> float:
        return self.rto
