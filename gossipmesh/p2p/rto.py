from typing import Optional


def calculate_rto(srtt: Optional[float], rttvar: Optional[float], clock_granularity: float = 0.01) -> float:
    """Calculate Retransmission Timeout (RTO) following RFC 6298."""
    if srtt is None or rttvar is None:
        return 1.0
    rto = srtt + max(clock_granularity, 4.0 * rttvar)
    return max(0.1, min(rto, 60.0))
