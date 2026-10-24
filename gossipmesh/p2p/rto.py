from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0, alpha: float = 0.125, beta: float = 0.25):
        self.rto: float = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None
        self.alpha = alpha
        self.beta = beta

    def update(self, rtt: float) -> None:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = (1 - self.beta) * self.rttvar + self.beta * abs(self.srtt - rtt)  # type: ignore[operator]
            self.srtt = (1 - self.alpha) * self.srtt + self.alpha * rtt
        self.rto = self.srtt + max(0.01, 4.0 * (self.rttvar or 0.0))

    def get_rto(self) -> float:
        return self.rto
