import time


def get_current_epoch(epoch_duration_seconds: int = 300) -> int:
    """Calculates the current rolling temporal epoch based on UNIX timestamp."""
    if epoch_duration_seconds <= 0:
        raise ValueError("Epoch duration must be greater than zero.")
    return int(time.time() // epoch_duration_seconds)


def get_epoch_bounds(epoch: int, epoch_duration_seconds: int = 300) -> tuple[int, int]:
    """Returns the start and end UNIX timestamps for a given epoch."""
    if epoch_duration_seconds <= 0:
        raise ValueError("Epoch duration must be greater than zero.")
    start_time = epoch * epoch_duration_seconds
    return start_time, start_time + epoch_duration_seconds


def is_epoch_valid(
    epoch: int,
    current_epoch: int,
    allowed_drift_past: int = 1,
    allowed_drift_future: int = 1,
) -> bool:
    """Validates if a given epoch falls within the acceptable drift window."""
    if allowed_drift_past < 0 or allowed_drift_future < 0:
        raise ValueError("Drift tolerances must be non-negative.")
    return (current_epoch - allowed_drift_past) <= epoch <= (current_epoch + allowed_drift_future)
