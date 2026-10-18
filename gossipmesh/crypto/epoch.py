import time

EPOCH_DURATION_SECONDS = 60

def get_current_epoch(timestamp: float | None = None) -> int:
    """Calculates the current rolling temporal epoch based on default or provided timestamp."""
    ts = timestamp if timestamp is not None else time.time()
    return int(ts // EPOCH_DURATION_SECONDS)

def get_epoch_time_window(epoch: int) -> tuple[float, float]:
    """Returns the start and end timestamps (inclusive/exclusive) for a given epoch."""
    start = epoch * EPOCH_DURATION_SECONDS
    return start, start + EPOCH_DURATION_SECONDS

def is_epoch_valid(epoch: int, tolerance_epochs: int = 1, timestamp: float | None = None) -> bool:
    """Validates if an epoch is within an acceptable temporal window (tolerance)."""
    current_epoch = get_current_epoch(timestamp)
    return abs(current_epoch - epoch) <= tolerance_epochs
