from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0):
        self.rto = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None

    def update(self, measured_rtt: float) -> float:
        if self.srtt is None:
            self.srtt = measured_rtt
            self.rttvar = measured_rtt / 2.0
        else:
            self.rttvar = (
                0.75 * self.rttvar + 0.25 * abs(self.srtt - measured_rtt)
                if self.rttvar is not None
                else measured_rtt / 2.0
            )
            self.srtt = 0.875 * self.srtt + 0.125 * measured_rtt

        rttvar_val = self.rttvar if self.rttvar is not None else 0.0
        self.rto = (self.srtt if self.srtt is not None else 1.0) + max(0.01, 4.0 * rttvar_val)
        return self.rto
