import time
from typing import Dict, Tuple


class LoginThrottler:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, Tuple[int, float]] = {}

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        if key not in self.attempts:
            return False
        count, reset_time = self.attempts[key]
        if now > reset_time:
            del self.attempts[key]
            return False
        return count >= self.max_attempts

    def record_attempt(self, key: str) -> None:
        now = time.time()
        if key not in self.attempts:
            self.attempts[key] = (1, now + self.window_seconds)
        else:
            count, reset_time = self.attempts[key]
            if now > reset_time:
                self.attempts[key] = (1, now + self.window_seconds)
            else:
                self.attempts[key] = (count + 1, reset_time)


login_throttler = LoginThrottler()
