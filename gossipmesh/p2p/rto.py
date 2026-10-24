from typing import Optional


def calculate_rto(srtt: Optional[float], rttvar: Optional[float]) -> float:
    if srtt is None or rttvar is None:
        return 1.0
    return float(srtt) + 4.0 * float(rttvar)
