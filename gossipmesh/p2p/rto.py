from typing import Optional


class RTOCalculator:
    def __init__(self, initial_rto: float = 1.0):
        self.rto = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None

    def update(self, rtt: float) -> float:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = (1 - 0.25) * (self.rttvar if self.rttvar is not None else 0.0) + 0.25 * abs(self.srtt - rtt)
            self.srtt = (1 - 0.125) * self.srtt + 0.125 * rtt

        assert self.srtt is not None
        assert self.rttvar is not None
        self.rto = self.srtt + max(0.01, 4.0 * self.rttvar)
        return self.rto
