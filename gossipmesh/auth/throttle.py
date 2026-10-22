"""Login throttling, progressive delay, and brute-force account lockout (Task 41)."""

from collections import deque
from datetime import datetime, timezone, timedelta
import threading
from typing import Dict, Tuple, Optional


class LoginThrottler:
    """Thread-safe login throttling and progressive delay / account lockout.

    Policy:
    - Max failed attempts: 5 in a 15-minute window
    - Lockout duration: 15 minutes (900 seconds)
    - Progressive delays:
        Attempts 1-2: 0.0s
        Attempt 3:    1.0s
        Attempt 4:    2.0s
        Attempt 5+:   Lockout (returns is_locked=True)
    """

    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 900,
        lockout_seconds: int = 900,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._lock = threading.Lock()
        self._failures: Dict[str, deque] = {}
        self._lockouts: Dict[str, datetime] = {}

    def check_lockout(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """Returns (is_locked, remaining_lockout_seconds)."""
        clean_id = identifier.strip().lower()
        with self._lock:
            now = datetime.now(timezone.utc)
            locked_until = self._lockouts.get(clean_id)
            if locked_until:
                if now < locked_until:
                    remaining = int((locked_until - now).total_seconds())
                    return True, max(1, remaining)
                else:
                    del self._lockouts[clean_id]
            return False, None

    def record_failure(self, identifier: str) -> Tuple[bool, Optional[int], float]:
        """Records a failed attempt.
        Returns (is_now_locked, remaining_seconds, progressive_delay_seconds).
        """
        clean_id = identifier.strip().lower()
        with self._lock:
            now = datetime.now(timezone.utc)
            now_ts = now.timestamp()
            if clean_id not in self._failures:
                self._failures[clean_id] = deque()

            dq = self._failures[clean_id]
            cutoff = now_ts - self.window_seconds
            while dq and dq[0] < cutoff:
                dq.popleft()

            dq.append(now_ts)
            failure_count = len(dq)

            if failure_count >= self.max_attempts:
                locked_until = now + timedelta(seconds=self.lockout_seconds)
                self._lockouts[clean_id] = locked_until
                return True, self.lockout_seconds, 0.0

            delay = 0.0
            if failure_count == 3:
                delay = 1.0
            elif failure_count == 4:
                delay = 2.0

            return False, None, delay

    def record_success(self, identifier: str):
        """Clears failed attempts and lockouts upon successful login."""
        clean_id = identifier.strip().lower()
        with self._lock:
            self._failures.pop(clean_id, None)
            self._lockouts.pop(clean_id, None)

    def reset(self):
        """Clears all tracking state."""
        with self._lock:
            self._failures.clear()
            self._lockouts.clear()


login_throttler = LoginThrottler()
