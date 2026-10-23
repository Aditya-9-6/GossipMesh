class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0) -> None:
        self.rto = initial_rto

    def update(self, rtt: float) -> None:
        pass

    def get_rto(self) -> float:
        return self.rto
