from typing import Dict, Tuple, Optional, List
import time


class LoginThrottler:
    """Throttles login attempts based on IP or username to prevent brute-force attacks."""

    def __init__(
        self,
        limit: int = 5,
        window: int = 300,
        max_attempts: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> None:
        self.limit = limit if max_attempts is None else max_attempts
        self.window = window if window_seconds is None else window_seconds
        self.max_attempts = self.limit
        self.window_seconds = self.window
        self._attempts: Dict[str, Tuple[int, float]] = {}
        self.attempts: Dict[str, List[float]] = {}
        self.attempts_tuple: Dict[str, Tuple[int, float]] = {}

    def check_rate_limit(self, key: str, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if key not in self._attempts:
            return True
        count, first_attempt = self._attempts[key]
        if now - first_attempt > self.window_seconds:
            del self._attempts[key]
            return True
        return count < self.max_attempts

    def check(self, key: str) -> bool:
        now = time.time()
        history = self.attempts.get(key, [])
        history = [t for t in history if now - t < self.window]
        self.attempts[key] = history
        return len(history) < self.limit

    def record(self, key: str) -> None:
        now = time.time()
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(now)
        self.record_attempt(key)

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        if key not in self.attempts_tuple:
            return not self.check(key)
        count, window_start = self.attempts_tuple[key]
        if now - window_start > self.window_seconds:
            return False
        return count >= self.max_attempts or not self.check(key)

    def record_attempt(self, key: str, success: bool = False, current_time: Optional[float] = None) -> None:
        now = current_time if current_time is not None else time.time()
        if success:
            self._attempts.pop(key, None)
            self.attempts_tuple.pop(key, None)
            return
        if key not in self._attempts:
            self._attempts[key] = (1, now)
        else:
            count, first_attempt = self._attempts[key]
            if now - first_attempt > self.window_seconds:
                self._attempts[key] = (1, now)
            else:
                self._attempts[key] = (count + 1, first_attempt)

        if key not in self.attempts_tuple:
            self.attempts_tuple[key] = (1, now)
            return
        count_t, window_start = self.attempts_tuple[key]
        if now - window_start > self.window_seconds:
            self.attempts_tuple[key] = (1, now)
        else:
            self.attempts_tuple[key] = (count_t + 1, window_start)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)
        self.attempts.pop(key, None)
        self.attempts_tuple.pop(key, None)


login_throttler = LoginThrottler()
