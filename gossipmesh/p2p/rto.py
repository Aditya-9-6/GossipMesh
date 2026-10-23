from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0):
        self.rto = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None

    def update(self, rtt: float):
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = 0.75 * self.rttvar + 0.25 * abs(self.srtt - rtt) if self.rttvar is not None else rtt / 2.0
            self.srtt = 0.875 * self.srtt + 0.125 * rtt
        self.rto = self.srtt + max(0.01, 4.0 * (self.rttvar or 0.0))
