import time


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0):
        self.rto = initial_rto
        self.srtt: float | None = None
        self.rttvar: float | None = None

    def update(self, rtt: float):
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            alpha = 0.125
            beta = 0.25
            rttvar_val = self.rttvar if self.rttvar is not None else 0.0
            self.rttvar = (1 - beta) * rttvar_val + beta * abs(self.srtt - rtt)
            self.srtt = (1 - alpha) * self.srtt + alpha * rtt

        rttvar_val = self.rttvar if self.rttvar is not None else 0.0
        srtt_val = self.srtt if self.srtt is not None else self.rto
        self.rto = srtt_val + max(0.01, 4.0 * rttvar_val)

    def get_rto(self) -> float:
        return self.rto
