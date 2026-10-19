from typing import Optional


class RTOEstimator:
    """Jacobson/Karels RTO estimator with exponential moving average."""

    def __init__(self, alpha: float = 0.125, beta: float = 0.25, initial_rto: float = 1.0):
        self.alpha = alpha
        self.beta = beta
        self._srtt: Optional[float] = None
        self._rttvar: Optional[float] = None
        self._rto = initial_rto

    def update(self, measured_rtt: float) -> float:
        if self._srtt is None:
            self._srtt = measured_rtt
            self._rttvar = measured_rtt / 2.0
        else:
            rttvar = self._rttvar if self._rttvar is not None else (measured_rtt / 2.0)
            srtt = self._srtt if self._srtt is not None else measured_rtt
            self._rttvar = (1.0 - self.beta) * rttvar + self.beta * abs(srtt - measured_rtt)
            self._srtt = (1.0 - self.alpha) * srtt + self.alpha * measured_rtt

        srtt_val = self._srtt if self._srtt is not None else 1.0
        rttvar_val = self._rttvar if self._rttvar is not None else 0.5
        self._rto = srtt_val + max(0.01, 4.0 * rttvar_val)
        return self._rto

    @property
    def rto(self) -> float:
        return self._rto
