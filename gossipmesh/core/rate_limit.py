import time
from typing import Tuple
from gossipmesh.db.redis import redis_client
from gossipmesh.core.exceptions import RateLimitError


class RateLimiter:
    """Redis-backed rate limiter."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window

    def _get_key(self, identifier: str, limit_type: str) -> str:
        return f"ratelimit:{limit_type}:{identifier}"

    def check_limit(self, identifier: str, limit_type: str) -> Tuple[bool, int, int]:
        """
        Check if the request is within the rate limit.
        Returns: (is_allowed, remaining, reset_time)
        """
        key = self._get_key(identifier, limit_type)

        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.pttl(key)
        results = pipe.execute()

        current_count = results[0]
        ttl_ms = results[1]

        # Ensure correct type extraction for mock handling
        try:
            current_count_int = int(current_count)
        except Exception:
            current_count_int = 0

        try:
            ttl_ms_int = int(ttl_ms)
        except Exception:
            ttl_ms_int = 0

        if current_count_int == 1:
            redis_client.expire(key, self.window)
            reset_time = int(time.time() + self.window)
            remaining = self.limit - 1
        else:
            if ttl_ms_int > 0:
                reset_time = int(time.time() + (ttl_ms_int / 1000.0))
            else:
                reset_time = int(time.time() + self.window)

            remaining = max(0, self.limit - current_count_int)

        is_allowed = bool(current_count_int <= self.limit)

        return is_allowed, remaining, reset_time

    def enforce(self, identifier: str, limit_type: str) -> Tuple[int, int]:
        is_allowed, remaining, reset_time = self.check_limit(identifier, limit_type)
        if not is_allowed:
            raise RateLimitError(
                message="Rate limit exceeded", details={"limit": self.limit, "remaining": 0, "reset": reset_time}
            )
        return remaining, reset_time
