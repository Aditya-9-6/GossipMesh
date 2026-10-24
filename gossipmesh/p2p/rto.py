class RTOEstimator:
    def __init__(self):
        self.srtt: float | None = None
        self.rttvar: float | None = None

    def update(self, rtt: float) -> None:
        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            assert self.rttvar is not None
            err = rtt - self.srtt
            self.srtt = self.srtt + 0.125 * err
            self.rttvar = 0.75 * self.rttvar + 0.25 * abs(err)

    def get_rto(self) -> float:
        if self.srtt is None or self.rttvar is None:
            return 1.0
        return self.srtt + max(0.01, 4.0 * self.rttvar)
