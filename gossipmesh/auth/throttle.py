from typing import Any


class LoginThrottler:
    def __init__(self, rate_limit: int = 5, period: int = 300) -> None:
        self.rate_limit = rate_limit
        self.period = period

    def check(self, key: str) -> bool:
        return True

    def record_failure(self, key: str) -> None:
        pass

    def clear(self, key: str) -> None:
        pass


login_throttler = LoginThrottler()
