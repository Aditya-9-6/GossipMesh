import time
import os
import logging

threading = __import__("threading")
try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)


class AdaptiveScatterGovernor:
    """Localized resource-aware governor that dynamically adjusts individual node
    gossip fanout (scatter-width) based on real-time OS process CPU and memory utilization.
    Uses a low-pass smoothing filter to prevent oscillation.
    """

    def __init__(
        self,
        base_scatter: int = 4,
        min_scatter: int = 1,
        cpu_threshold: float = 80.0,
        mem_threshold: float = 85.0,
        alpha: float = 0.5,
    ):
        self.base_scatter = base_scatter
        self.min_scatter = min_scatter
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold
        self.alpha = alpha  # Smoothing factor for low-pass filter
        self._smoothed_cpu = 0.0
        self._smoothed_mem = 0.0
        self._last_update = 0.0
        self._current_scatter = float(base_scatter)
        self._lock = threading.Lock()

        if psutil is not None:
            try:
                self._process = psutil.Process(os.getpid())
                # Warm up cpu percent non-blocking
                self._process.cpu_percent(interval=None)
            except Exception:
                self._process = None
        else:
            self._process = None

    def sample_metrics(self) -> tuple[float, float]:
        """Polls local process resource usage under a strict non-blocking threshold."""
        cpu_pct = 0.0
        mem_pct = 0.0
        if self._process is not None:
            try:
                cpu_pct = self._process.cpu_percent(interval=None)
                mem_pct = self._process.memory_percent()
            except Exception:
                pass
        return cpu_pct, mem_pct

    def update(self) -> int:
        """Updates smoothed metrics and computes the adaptive scatter-width."""
        with self._lock:
            raw_cpu, raw_mem = self.sample_metrics()

            # Low-pass filter smoothing: smoothed = alpha * raw + (1 - alpha) * smoothed
            self._smoothed_cpu = self.alpha * raw_cpu + (1.0 - self.alpha) * self._smoothed_cpu
            self._smoothed_mem = self.alpha * raw_mem + (1.0 - self.alpha) * self._smoothed_mem

            # Determine penalty scaling factor based on thresholds
            cpu_load_ratio = self._smoothed_cpu / max(self.cpu_threshold, 1.0)
            mem_load_ratio = self._smoothed_mem / max(self.mem_threshold, 1.0)
            max_load_ratio = max(cpu_load_ratio, mem_load_ratio)

            if max_load_ratio > 1.0:
                # Scale down proportionally as load exceeds safety bounds
                reduction_factor = 1.0 / max_load_ratio
                target_scatter = float(self.base_scatter) * reduction_factor
            else:
                target_scatter = float(self.base_scatter)

            # Clamp scatter width between min_scatter and base_scatter
            clamped = max(float(self.min_scatter), min(float(self.base_scatter), target_scatter))

            # Smooth scatter transitions as well
            self._current_scatter = self.alpha * clamped + (1.0 - self.alpha) * self._current_scatter

            return max(self.min_scatter, round(self._current_scatter))

    def get_scatter(self) -> int:
        """Returns the current adapted scatter-width."""
        with self._lock:
            return max(self.min_scatter, round(self._current_scatter))

    def get_metrics(self) -> dict:
        """Returns telemetry information for monitoring."""
        with self._lock:
            return {
                "smoothed_cpu": self._smoothed_cpu,
                "smoothed_mem": self._smoothed_mem,
                "current_scatter": self.get_scatter(),
                "base_scatter": self.base_scatter,
            }
