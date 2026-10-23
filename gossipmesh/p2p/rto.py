from __future__ import annotations


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0, alpha: float = 0.125, beta: float = 0.25):
        self.rto = initial_rto
        self.srtt: float | None = None
        self.rttvar: float | None = None
        self.alpha = alpha
        self.beta = beta

    def update_rtt(self, rtt: float) -> None:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - rtt)
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * rtt
        assert self.srtt is not None
        assert self.rttvar is not None
        self.rto = self.srtt + max(0.01, 4.0 * self.rttvar)

    def backoff(self) -> None:
        self.rto = min(60.0, self.rto * 2.0)

    get_rto = lambda self: self.rto
