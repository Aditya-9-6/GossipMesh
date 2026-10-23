from typing import Optional


class RTOEstimator:
    def __init__(self) -> None:
        self.rto: Optional[float] = 1.0

    def update(self, sample: float) -> None:
        if self.rto is not None:
            self.rto = self.rto * 0.8 + sample * 0.2
        else:
            self.rto = sample
