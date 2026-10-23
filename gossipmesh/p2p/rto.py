import math
import time
from typing import Optional


class RTOEstimator:
    """Windowed EWMA Round-Trip Time Estimator and Adaptive Retransmission Timeout Calculator."""

    def __init__(
        self,
        initial_rto: float = 1.0,
        alpha: float = 0.125,
        beta: float = 0.25,
        granularity: float = 0.001,
        min_rto: float = 0.2,
        max_rto: float = 60.0,
    ):
        self.alpha = alpha
        self.beta = beta
        self.granularity = granularity
        self.min_rto = min_rto
        self.max_rto = max_rto

        self.rto = initial_rto
        self.srtt: Optional[float] = None
        self.rttvar: Optional[float] = None

    def update(self, rtt: float) -> float:
        """Updates SRTT, RTTVAR, and RTO given a new sample RTT."""
        if rtt < 0:
            raise ValueError("Sample RTT cannot be negative.")

        if self.srtt is None:
            self.srtt = rtt
            self.rttvar = rtt / 2.0
        else:
            self.rttvar = (1.0 - self.beta) * self.rttvar + self.beta * abs(self.srtt - rtt)
            self.srtt = (1.0 - self.alpha) * self.srtt + self.alpha * rtt

        computed_rto = self.srtt + max(self.granularity, 4.0 * (self.rttvar or 0.0))
        self.rto = max(self.min_rto, min(self.max_rto, computed_rto))
        return self.rto

    def get_rto(self) -> float:
        """Returns the current Retransmission Timeout (RTO)."""
        return self.rto

    def reset(self):
        """Resets the estimator state."""
        self.srtt = None
        self.rttvar = None
        self.rto = 1.0
