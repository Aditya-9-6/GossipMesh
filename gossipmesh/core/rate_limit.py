from typing import Tuple


class RateLimitError(Exception):
    pass


class RateLimiter:
    def __init__(self, limit: int, window: int) -> None:
        self.limit = limit
        self.window = window

    def enforce(self, identifier: str, limit_type: str) -> Tuple[int, int]:
        return self.limit - 1, 3600
