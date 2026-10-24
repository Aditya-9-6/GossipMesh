import time
from typing import Any, Dict, Tuple


class LoginThrottler:
    def __init__(self, rate_limit: int = 5, period: int = 300, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self.rate_limit = rate_limit
        self.period = period
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, Tuple[int, float]] = {}

    def check(self, key: str) -> bool:
        return not self.is_rate_limited(key)

    def record_failure(self, key: str) -> None:
        self.record_attempt(key)

    def clear(self, key: str) -> None:
        self.reset(key)

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        if key not in self.attempts:
            return False
        count, window_start = self.attempts[key]
        if now - window_start > self.window_seconds:
            return False
        return count >= self.max_attempts

    def record_attempt(self, key: str) -> None:
        now = time.time()
        if key not in self.attempts:
            self.attempts[key] = (1, now)
            return
        count, window_start = self.attempts[key]
        if now - window_start > self.window_seconds:
            self.attempts[key] = (1, now)
        else:
            self.attempts[key] = (count + 1, window_start)

    def reset(self, key: str) -> None:
        self.attempts.pop(key, None)


login_throttler = LoginThrottler()
