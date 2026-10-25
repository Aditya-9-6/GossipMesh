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

    def record_failure(self, key: str) -> Tuple[bool, int, float]:
        now = time.time()
        self.record(key)
        attempts, _ = self.attempts_tuple.get(key, (0, now))
        if attempts >= self.max_attempts:
            self.lockouts[key] = now + self.window_seconds
            return True, self.window_seconds, float(self.window_seconds)
        return False, 0, 0.0

    def record_success(self, key: str) -> None:
        self.reset(key)

    def check_lockout(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        lock_until = self.lockouts.get(key, 0)
        if now < lock_until:
            return True, int(lock_until - now)
        return False, 0

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


login_throttler = LoginThrottler()
