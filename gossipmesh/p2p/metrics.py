import enum
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class PeerTier(str, enum.Enum):
    """Peer performance tiers based on sustained bandwidth throughput."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BandwidthConfig:
    """Configuration parameters for windowed EWMA bandwidth profiler."""
    alpha: float = 0.2
    window_seconds: float = 60.0
    high_tier_threshold_bps: float = 1_048_576.0  # 1 MB/s
    medium_tier_threshold_bps: float = 131_072.0  # 128 KB/s


@dataclass
class EWMASample:
    timestamp: float
    bytes_transferred: int


class WindowedEWMABandwidthProfiler:
    """Thread-safe windowed EWMA bandwidth profiler for dynamic peer tiering."""

    def __init__(self, config: Optional[BandwidthConfig] = None) -> None:
        self.config = config or BandwidthConfig()
        self._lock = threading.Lock()
        self._current_ewma_bps: float = 0.0
        self._samples: List[EWMASample] = []
        self._last_update_time: float = time.time()
        self._total_bytes: int = 0
        self._total_samples: int = 0

    def record_transfer(self, bytes_count: int, timestamp: Optional[float] = None) -> None:
        """Records a data transfer event and updates the windowed EWMA bandwidth."""
        if bytes_count <= 0:
            return
        now = timestamp if timestamp is not None else time.time()
        with self._lock:
            self._purge_expired_samples(now)
            self._samples.append(EWMASample(timestamp=now, bytes_transferred=bytes_count))
            self._total_bytes += bytes_count
            self._total_samples += 1
            self._recompute_ewma(now)

    def _purge_expired_samples(self, current_time: float) -> None:
        """Removes samples outside the sliding time window."""
        cutoff = current_time - self.config.window_seconds
        while self._samples and self._samples[0].timestamp < cutoff:
            self._samples.pop(0)

    def _recompute_ewma(self, current_time: float) -> None:
        """Computes EWMA over active window samples."""
        if not self._samples:
            self._current_ewma_bps = 0.0
            self._last_update_time = current_time
            return

        # Aggregate bytes per second in window
        window_bytes = sum(s.bytes_transferred for s in self._samples)
        actual_window = max(1.0, current_time - self._samples[0].timestamp)
        instantaneous_bps = window_bytes / actual_window

        if self._current_ewma_bps == 0.0:
            self._current_ewma_bps = instantaneous_bps
        else:
            alpha = self.config.alpha
            self._current_ewma_bps = (alpha * instantaneous_bps) + ((1.0 - alpha) * self._current_ewma_bps)
        self._last_update_time = current_time

    def get_bandwidth_bps(self, current_time: Optional[float] = None) -> float:
        """Returns the current EWMA bandwidth in bytes per second."""
        now = current_time if current_time is not None else time.time()
        with self._lock:
            self._purge_expired_samples(now)
            if not self._samples and (now - self._last_update_time > self.config.window_seconds):
                self._current_ewma_bps = 0.0
            return self._current_ewma_bps

    def get_tier(self, current_time: Optional[float] = None) -> PeerTier:
        """Classifies the peer into a performance tier based on current bandwidth."""
        bps = self.get_bandwidth_bps(current_time)
        if not self._samples and bps == 0.0:
            return PeerTier.UNKNOWN
        if bps >= self.config.high_tier_threshold_bps:
            return PeerTier.HIGH
        elif bps >= self.config.medium_tier_threshold_bps:
            return PeerTier.MEDIUM
        else:
            return PeerTier.LOW

    def get_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive thread-safe snapshot metrics."""
        now = time.time()
        with self._lock:
            self._purge_expired_samples(now)
            current_bps = self._current_ewma_bps
            tier = self.get_tier(now)
            total_bytes = self._total_bytes
            total_samples = self._total_samples
            active_samples_count = len(self._samples)
        return {
            "current_bandwidth_bps": current_bps,
            "tier": tier.value,
            "total_bytes": total_bytes,
            "total_samples": total_samples,
            "active_samples_count": active_samples_count,
            "window_seconds": self.config.window_seconds,
        }

    def reset(self) -> None:
        """Resets all profiler state."""
        with self._lock:
            self._samples.clear()
            self._current_ewma_bps = 0.0
            self._total_bytes = 0
            self._total_samples = 0
            self._last_update_time = time.time()


class PeerTierManager:
    """Manages bandwidth profilers and tiering classifications across multiple peers."""

    def __init__(self, default_config: Optional[BandwidthConfig] = None) -> None:
        self.default_config = default_config or BandwidthConfig()
        self._profilers: Dict[str, WindowedEWMABandwidthProfiler] = {}
        self._lock = threading.Lock()

    def get_profiler(self, peer_id: str) -> WindowedEWMABandwidthProfiler:
        """Retrieves or creates a bandwidth profiler for the given peer."""
        with self._lock:
            if peer_id not in self._profilers:
                self._profilers[peer_id] = WindowedEWMABandwidthProfiler(self.default_config)
            return self._profilers[peer_id]

    def record_peer_transfer(self, peer_id: str, bytes_count: int, timestamp: Optional[float] = None) -> None:
        """Records a transfer for a specific peer."""
        profiler = self.get_profiler(peer_id)
        profiler.record_transfer(bytes_count, timestamp)

    def get_peer_tier(self, peer_id: str) -> PeerTier:
        """Returns the tier of a specific peer."""
        with self._lock:
            profiler = self._profilers.get(peer_id)
            if not profiler:
                return PeerTier.UNKNOWN
        return profiler.get_tier()

    def remove_peer(self, peer_id: str) -> None:
        """Removes tracking state for a disconnected peer."""
        with self._lock:
            self._profilers.pop(peer_id, None)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Returns metrics across all tracked peers."""
        with self._lock:
            return {pid: prof.get_metrics() for pid, prof in self._profilers.items()}
