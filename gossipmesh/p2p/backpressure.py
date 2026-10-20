import enum
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


class BackpressureState(str, enum.Enum):
    """Backpressure operating states for connection pool saturation levels."""

    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"
    SHEDDING = "shedding"


@dataclass(frozen=True)
class BackpressureConfig:
    """Configuration for saturation thresholds and decay parameters."""

    elevated_threshold: float = 0.70
    critical_threshold: float = 0.85
    shedding_threshold: float = 0.95
    decay_rate: float = 0.1


class BackpressureSignalManager:
    """Manages system saturation telemetry and determines backpressure signaling
    to drop low-priority gossip streams when capacity utilization exceeds limits.
    Thread-safe with O(1) operations."""

    def __init__(self, config: Optional[BackpressureConfig] = None) -> None:
        self.config = config or BackpressureConfig()
        self._lock = threading.Lock()
        self._current_saturation: float = 0.0
        self._state: BackpressureState = BackpressureState.NORMAL
        self._last_updated: float = time.time()
        self._metrics_count: int = 0

    def update_saturation(self, current_connections: int, max_connections: int) -> BackpressureState:
        """Updates saturation ratio based on active connections and recalculates state."""
        if max_connections <= 0:
            ratio = 1.0
        else:
            ratio = min(max(0.0, float(current_connections) / float(max_connections)), 1.0)

        with self._lock:
            self._current_saturation = ratio
            self._last_updated = time.time()
            self._metrics_count += 1

            if ratio >= self.config.shedding_threshold:
                self._state = BackpressureState.SHEDDING
            elif ratio >= self.config.critical_threshold:
                self._state = BackpressureState.CRITICAL
            elif ratio >= self.config.elevated_threshold:
                self._state = BackpressureState.ELEVATED
            else:
                self._state = BackpressureState.NORMAL

            return self._state

    def get_state(self) -> BackpressureState:
        """Returns the current backpressure state."""
        with self._lock:
            return self._state

    def get_saturation(self) -> float:
        """Returns the current connection saturation ratio."""
        with self._lock:
            return self._current_saturation

    def should_drop_low_priority(self) -> bool:
        """Returns True if saturation exceeds critical threshold (>= 85%)."""
        with self._lock:
            return self._current_saturation >= self.config.critical_threshold

    def get_metrics(self) -> Dict[str, Any]:
        """Returns telemetry metrics for backpressure management."""
        with self._lock:
            return {
                "saturation": self._current_saturation,
                "state": self._state.value,
                "should_drop_low_priority": self._current_saturation >= self.config.critical_threshold,
                "last_updated": self._last_updated,
                "metrics_count": self._metrics_count,
            }

    def reset(self) -> None:
        """Resets backpressure state."""
        with self._lock:
            self._current_saturation = 0.0
            self._state = BackpressureState.NORMAL
            self._last_updated = time.time()
            self._metrics_count = 0
