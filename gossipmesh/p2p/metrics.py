import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class PeerTier(str, enum.Enum):
    """Classification tier for gossip peers based on sustained throughput."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BandwidthProfilerConfig:
    """Configuration parameters for windowed EWMA bandwidth profiler."""

    window_size_seconds: float = 60.0
    bucket_count: int = 6
    alpha: float = 0.3
    high_tier_threshold_bps: float = 1_000_000.0  # 1 MB/s
    medium_tier_threshold_bps: float = 100_000.0  # 100 KB/s


@dataclass
class PeerBandwidthSample:
    """Represents a data transfer sample."""

    timestamp: float
    bytes_transferred: int


class WindowedEWMABandwidthProfiler:
    """Thread-safe windowed EWMA bandwidth profiler for dynamic peer tiering."""

    def __init__(self, config: Optional[BandwidthProfilerConfig] = None) -> None:
        self.config = config or BandwidthProfilerConfig()
        self._lock = threading.Lock()
        self._samples: List[PeerBandwidthSample] = []
        self._ewma_bps: float = 0.0
        self._last_update_time: float = time.time()

    def record_transfer(self, bytes_transferred: int, timestamp: Optional[float] = None) -> None:
        """Records a completed transfer of given byte size in O(1) amortized time."""
        if bytes_transferred <= 0:
            return
        now = timestamp if timestamp is not None else time.time()
        with self._lock:
            self._prune_expired_samples(now)
            self._samples.append(PeerBandwidthSample(timestamp=now, bytes_transferred=bytes_transferred))
            self._recalculate_ewma(now)

    def _prune_expired_samples(self, current_time: float) -> None:
        """Removes samples older than the rolling window size."""
        cutoff = current_time - self.config.window_size_seconds
        while self._samples and self._samples[0].timestamp < cutoff:
            self._samples.pop(0)

    def _recalculate_ewma(self, current_time: float) -> None:
        """Updates the windowed EWMA bandwidth estimate."""
        self._prune_expired_samples(current_time)
        if not self._samples:
            self._ewma_bps = 0.0
            self._last_update_time = current_time
            return

        total_bytes = sum(s.bytes_transferred for s in self._samples)
        span = max(1.0, current_time - self._samples[0].timestamp)
        instantaneous_bps = total_bytes / span

        if self._ewma_bps == 0.0:
            self._ewma_bps = instantaneous_bps
        else:
            alpha = self.config.alpha
            self._ewma_bps = alpha * instantaneous_bps + (1.0 - alpha) * self._ewma_bps
        self._last_update_time = current_time

    def get_bandwidth_bps(self, current_time: Optional[float] = None) -> float:
        """Returns the current EWMA bandwidth estimate in bytes per second."""
        now = current_time if current_time is not None else time.time()
        with self._lock:
            self._prune_expired_samples(now)
            if not self._samples and self._ewma_bps > 0:
                self._ewma_bps = 0.0
            return self._ewma_bps

    def get_tier(self, current_time: Optional[float] = None) -> PeerTier:
        """Classifies the peer into HIGH, MEDIUM, or LOW tier based on bandwidth."""
        bps = self.get_bandwidth_bps(current_time)
        if bps >= self.config.high_tier_threshold_bps:
            return PeerTier.HIGH
        elif bps >= self.config.medium_tier_threshold_bps:
            return PeerTier.MEDIUM
        else:
            return PeerTier.LOW

    def get_metrics(self, current_time: Optional[float] = None) -> Dict[str, Any]:
        """Returns telemetry metrics dictionary for the profiler."""
        now = current_time if current_time is not None else time.time()
        with self._lock:
            self._prune_expired_samples(now)
            total_bytes = sum(s.bytes_transferred for s in self._samples)
            bps = self.get_bandwidth_bps(now)
            tier = self.get_tier(now)
            return {
                "ewma_bps": bps,
                "tier": tier.value,
                "active_samples": len(self._samples),
                "window_total_bytes": total_bytes,
                "window_size_seconds": self.config.window_size_seconds,
            }

    def reset(self) -> None:
        """Resets all profiler samples and EWMA state."""
        with self._lock:
            self._samples.clear()
            self._ewma_bps = 0.0
            self._last_update_time = time.time()


class PeerTierManager:
    """Manages bandwidth profilers across multiple peers and provides aggregate tiering."""

    def __init__(self, default_config: Optional[BandwidthProfilerConfig] = None) -> None:
        self.default_config = default_config or BandwidthProfilerConfig()
        self._lock = threading.Lock()
        self._profilers: Dict[str, WindowedEWMABandwidthProfiler] = {}

    def get_profiler(self, peer_id: str) -> WindowedEWMABandwidthProfiler:
        """Returns or creates a bandwidth profiler for the specified peer."""
        with self._lock:
            if peer_id not in self._profilers:
                self._profilers[peer_id] = WindowedEWMABandwidthProfiler(self.default_config)
            return self._profilers[peer_id]

    def record_peer_transfer(self, peer_id: str, bytes_transferred: int, timestamp: Optional[float] = None) -> None:
        """Records a transfer for a specific peer."""
        profiler = self.get_profiler(peer_id)
        profiler.record_transfer(bytes_transferred, timestamp=timestamp)

    def get_peer_tier(self, peer_id: str, current_time: Optional[float] = None) -> PeerTier:
        """Returns the tier of a specific peer."""
        with self._lock:
            profiler = self._profilers.get(peer_id)
            if not profiler:
                return PeerTier.UNKNOWN
        return profiler.get_tier(current_time)

    def remove_peer(self, peer_id: str) -> None:
        """Removes tracking state for a disconnected peer."""
        with self._lock:
            self._profilers.pop(peer_id, None)

    def get_all_metrics(self, current_time: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """Returns telemetry metrics across all active peer profilers."""
        with self._lock:
            profilers_snapshot = list(self._profilers.items())
        return {peer_id: profiler.get_metrics(current_time) for peer_id, profiler in profilers_snapshot}
