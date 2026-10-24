import time
from typing import Dict, Tuple, List


class LoginThrottler:
    def __init__(
        self,
        rate_limit: int = 5,
        period: int = 300,
        max_attempts: int = 5,
        window_seconds: int = 300,
        limit: int = 5,
        window: int = 300,
    ) -> None:
        self.rate_limit = rate_limit
        self.period = period
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.limit = limit
        self.window = window
        self.attempts: Dict[str, List[float]] = {}
        self.attempts_tuple: Dict[str, Tuple[int, float]] = {}
        self.lockouts: Dict[str, float] = {}

    def check(self, key: str) -> bool:
        now = time.time()
        history = self.attempts.get(key, [])
        history = [t for t in history if now - t < self.window]
        self.attempts[key] = history
        if len(history) >= self.limit:
            return False
        return not self.is_rate_limited(key)

    def record(self, key: str) -> None:
        now = time.time()
        if key not in self.attempts:
            self.attempts[key] = []
        self.attempts[key].append(now)
        self.record_attempt(key)

    def clear(self, key: str) -> None:
        self.reset(key)

    def is_rate_limited(self, key: str) -> bool:
        now = time.time()
        if key not in self.attempts_tuple:
            return not self.check(key)
        count, window_start = self.attempts_tuple[key]
        if now - window_start > self.window_seconds:
            self.attempts.pop(key, None)
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
        self.lockouts.pop(key, None)

    def check_lockout(self, username: str) -> Tuple[bool, int]:
        now = time.time()
        lock_until = self.lockouts.get(username, 0)
        if now < lock_until:
            return True, int(lock_until - now)
        limited = self.is_rate_limited(username)
        remaining = 0 if not limited else self.window_seconds
        return limited, remaining

    def record_failure(self, username: str) -> Tuple[bool, int, float]:
        self.record(username)
        now = time.time()
        attempts, _ = self.attempts_tuple.get(username, (0, now))
        if attempts >= self.max_attempts:
            self.lockouts[username] = now + self.window_seconds
            return True, self.window_seconds, 0.0
        limited = self.is_rate_limited(username)
        return limited, self.max_attempts, float(self.window_seconds)

    def record_success(self, username: str) -> None:
        self.reset(username)


login_throttler = LoginThrottler()
