class RTOEstimator:
    def __init__(self) -> None:
        self.rto = 1.0

    def update(self, rtt: float) -> None:
        self.rto = 0.8 * self.rto + 0.2 * rtt


__all__ = ["RTOEstimator"]
