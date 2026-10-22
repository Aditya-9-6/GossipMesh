import asyncio
import random
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Set


class PeerConnectionTrampoline:
    """High-throughput, non-blocking connection trampoline managing outbound peer dial
    attempts using exponential backoff with jitter and atomic state tracking."""

    def __init__(
        self, base_delay: float = 0.1, max_delay: float = 60.0, multiplier: float = 2.0, jitter: float = 0.1
    ) -> None:
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter_factor = jitter
        self._attempts: Dict[str, int] = {}
        self._next_retry: Dict[str, float] = {}
        self._states: Dict[str, str] = {}  # 'idle', 'dialing', 'connected', 'backed_off'
        self._lock = threading.Lock()

    def get_state(self, peer_id: str) -> str:
        with self._lock:
            return self._states.get(peer_id, "idle")

    def set_state(self, peer_id: str, state: str) -> None:
        with self._lock:
            self._states[peer_id] = state

    def can_dial(self, peer_id: str, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        with self._lock:
            state = self._states.get(peer_id, "idle")
            if state == "connected" or state == "dialing":
                return False
            next_time = self._next_retry.get(peer_id, 0.0)
            return now >= next_time

    def record_attempt(self, peer_id: str, success: bool, current_time: Optional[float] = None) -> float:
        now = current_time if current_time is not None else time.time()
        with self._lock:
            if success:
                self._attempts[peer_id] = 0
                self._next_retry[peer_id] = 0.0
                self._states[peer_id] = "connected"
                return 0.0
            else:
                attempts = self._attempts.get(peer_id, 0) + 1
                self._attempts[peer_id] = attempts
                delay = min(self.base_delay * (self.multiplier ** (attempts - 1)), self.max_delay)
                jitter_val = delay * self.jitter_factor * (random.random() * 2 - 1)
                actual_delay = max(0.0, delay + jitter_val)
                self._next_retry[peer_id] = now + actual_delay
                self._states[peer_id] = "backed_off"
                return actual_delay

    def reset(self, peer_id: str) -> None:
        with self._lock:
            self._attempts.pop(peer_id, None)
            self._next_retry.pop(peer_id, None)
            self._states.pop(peer_id, None)

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tracked_peers": len(self._states),
                "states": dict(self._states),
                "attempts": dict(self._attempts),
            }
