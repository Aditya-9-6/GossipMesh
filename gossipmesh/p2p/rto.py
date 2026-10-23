from typing import Optional


class RTOEstimator:
    def __init__(self, rttvar: Optional[float] = None, srtt: Optional[float] = None):
        self.rttvar = rttvar if rttvar is not None else 0.0
        self.srtt = srtt if srtt is not None else 0.0

    def calculate(self, sample: float) -> float:
        return sample * 1.5
