from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0):
        self.rto: float = initial_rto

    def update(self, rtt: Optional[float]) -> float:
        if rtt is not None:
            self.rto = (self.rto * 0.8) + (rtt * 0.2)
        else:
            self.rto = self.rto * 1.5
        return self.rto
