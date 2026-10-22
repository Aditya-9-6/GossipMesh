import time

class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0, min_rto: float = 0.2, max_rto: float = 60.0):
        self.rto = initial_rto
        self.min_rto = min_rto
        self.max_rto = max_rto
        self.srtt: float | None = None
        self.rttvar: float | None = None

    def update(self, rtt: float) -> float:
        if rtt < 0:
            raise ValueError("RTT cannot be negative")
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            alpha = 0.125
            beta = 0.25
            self.rttvar = (1 - beta) * self.rttvar + beta * abs(self.srtt - rtt)
            self.srtt = (1 - alpha) * self.srtt + alpha * rtt

        self.rto = self.srtt + max(0.01, 4.0 * (self.rttvar or 0.0))
        if self.rto < self.min_rto:
            self.rto = self.min_rto
        elif self.rto > self.max_rto:
            self.rto = self.max_rto

        return self.rto

    def get_rto(self) -> float:
        return self.rto

    def reset(self):
        self.srtt = None
        self.rttvar = None
        self.rto = 1.0
