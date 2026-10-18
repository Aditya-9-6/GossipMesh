import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import deque


@dataclass(frozen=True)
class BlacklistConfig:
    """Configuration parameters for sliding-window peer blacklisting."""
    window_seconds: float = 60.0
    max_failures: int = 5
    quarantine_seconds: float = 300.0


@dataclass
class PeerFailureRecord:
    """Tracks sliding window failure timestamps for a specific peer."""
    failures: deque = field(default_factory=deque)
    quarantined_until: float = 0.0
    total_violations: int = 0


class AdaptivePeerBlacklist:
    """Thread-safe sliding-window failure counter to dynamically blacklist misbehaving peers."""
    def __init__(self, config: Optional[BlacklistConfig] = None) -> None:
        self.config = config or BlacklistConfig()
        self._lock = threading.Lock()
        self._peers: Dict[str, PeerFailureRecord] = {}

    def record_failure(self, peer_id: str, now: Optional[float] = None) -> bool:
        """Records a failure for a peer within the sliding window.
        Returns True if the peer is now blacklisted/quarantined, False otherwise."""
        current_time = now if now is not None else time.time()
        
        with self._lock:
            record = self._get_or_create_peer_unlocked(peer_id)
            
            # If already quarantined, check if quarantine expired
            if record.quarantined_until > current_time:
                return True
            
            # Prune failures outside the sliding window
            window_start = current_time - self.config.window_seconds
            while record.failures and record.failures[0] < window_start:
                record.failures.popleft()
            
            # Record new failure
            record.failures.append(current_time)
            record.total_violations += 1
            
            # Check if threshold crossed
            if len(record.failures) >= self.config.max_failures:
                record.quarantined_until = current_time + self.config.quarantine_seconds
                return True
                
            return False

    def is_blacklisted(self, peer_id: str, now: Optional[float] = None) -> bool:
        """Checks whether a peer is currently quarantined/blacklisted."""
        current_time = now if now is not None else time.time()
        
        with self._lock:
            record = self._peers.get(peer_id)
            if not record:
                return False
                
            if record.quarantined_until > current_time:
                return True
                
            # If quarantine expired, clean up old failures
            window_start = current_time - self.config.window_seconds
            while record.failures and record.failures[0] < window_start:
                record.failures.popleft()
                
            return False

    def clear_peer(self, peer_id: str) -> None:
        """Manually lifts blacklist status and removes failure history for a peer."""
        with self._lock:
            if peer_id in self._peers:
                del self._peers[peer_id]

    def get_metrics(self, now: Optional[float] = None) -> Dict[str, Any]:
        """Returns telemetry metrics for active blacklists and tracked peers."""
        current_time = now if now is not None else time.time()
        with self._lock:
            active_quarantines = 0
            tracked_count = len(self._peers)
            for record in self._peers.values():
                if record.quarantined_until > current_time:
                    active_quarantines += 1
            return {
                "tracked_peers": tracked_count,
                "active_quarantines": active_quarantines,
                "window_seconds": self.config.window_seconds,
                "max_failures": self.config.max_failures,
                "quarantine_seconds": self.config.quarantine_seconds,
            }

    def _get_or_create_peer_unlocked(self, peer_id: str) -> PeerFailureRecord:
        if peer_id not in self._peers:
            self._peers[peer_id] = PeerFailureRecord()
        return self._peers[peer_id]
