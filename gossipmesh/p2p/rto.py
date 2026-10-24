from typing import Optional


class RTOEstimator:
    def __init__(self, initial_rto: float = 1.0) -> None:
        self.rto = initial_rto

    def update(self, rtt: float) -> None:
        self.rto = (self.rto * 0.8) + (rtt * 0.2)

    def get_rto(self) -> float:
        return self.rto


def calculate_rto(srtt: Optional[float], rttvar: float, rtt: float) -> float:
    base_srtt = srtt if srtt is not None else rtt
    return base_srtt + 4.0 * rttvar
