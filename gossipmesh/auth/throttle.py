from typing import Dict, Tuple, Optional
import time


class LoginThrottler:
    """Throttles login attempts based on IP or username to prevent brute-force attacks."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: Dict[str, Tuple[int, float]] = {}

    def check_rate_limit(self, key: str, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if key not in self._attempts:
            return True
        count, first_attempt = self._attempts[key]
        if now - first_attempt > self.window_seconds:
            del self._attempts[key]
            return True
        return count < self.max_attempts

    def record_attempt(self, key: str, success: bool, current_time: Optional[float] = None) -> None:
        now = current_time if current_time is not None else time.time()
        if success:
            self._attempts.pop(key, None)
            return
        if key not in self._attempts:
            self._attempts[key] = (1, now)
        else:
            count, first_attempt = self._attempts[key]
            if now - first_attempt > self.window_seconds:
                self._attempts[key] = (1, now)
            else:
                self._attempts[key] = (count + 1, first_attempt)


login_throttler = LoginThrottler()
