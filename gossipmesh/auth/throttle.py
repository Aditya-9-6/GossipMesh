import time
from typing import Dict, Tuple, List


class LoginThrottler:
    def __init__(self, limit: int = 5, window: int = 300) -> None:
        self.limit = limit
        self.window = window
        self.max_attempts = limit
        self.window_seconds = window
        self.attempts: dict[str, list[float]] = {}
        self.attempts_tuple: Dict[str, Tuple[int, float]] = {}

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

    def record_attempt(self, key: str) -> None:
        now = time.time()
        if key not in self.attempts_tuple:
            self.attempts_tuple[key] = (1, now)
            return
        count, window_start = self.attempts_tuple[key]
        if now - window_start > self.window_seconds:
            self.attempts_tuple[key] = (1, now)
        else:
            self.attempts_tuple[key] = (count + 1, window_start)

    def reset(self, key: str) -> None:
        self.attempts.pop(key, None)
        self.attempts_tuple.pop(key, None)

    def check_lockout(self, username: str) -> Tuple[bool, int]:
        limited = self.is_rate_limited(username)
        remaining = 0 if not limited else self.window_seconds
        return limited, remaining

    def record_failure(self, username: str) -> Tuple[bool, int, float]:
        self.record(username)
        limited = self.is_rate_limited(username)
        return limited, self.max_attempts, float(self.window_seconds)

    def record_success(self, username: str) -> None:
        self.reset(username)


login_throttler = LoginThrottler()
