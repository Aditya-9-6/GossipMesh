"""Retransmission Timeout (RTO) estimator."""


class RTOEstimator:
    """Estimates network RTO using Jacobson/Karels algorithm."""

    def __init__(self, initial_rto: float = 1.0):
        self.rto = initial_rto

    def update(self, rtt: float) -> None:
        self.rto = 0.8 * self.rto + 0.2 * rtt
