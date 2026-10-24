import time


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0):
        self.rto = initial_rto
        self.srtt: float | None = None
        self.rttvar: float | None = None

    def update(self, rtt: float) -> None:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = (1 - 0.25) * self.rttvar + 0.25 * abs(self.srtt - rtt)
            self.srtt = (1 - 0.125) * self.srtt + 0.125 * rtt
        self.rto = self.srtt + max(0.01, 4 * self.rttvar)

    def get_rto(self) -> float:
        return self.rto
