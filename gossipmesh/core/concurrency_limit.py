import contextlib
import time
from typing import Generator
import uuid
from gossipmesh.db.redis import redis_client
from gossipmesh.core.exceptions import ConcurrencyLimitError

class ConcurrencyLimiter:
    """Redis-backed concurrency limiter."""
    def __init__(self, limit: int, timeout_seconds: int = 300):
        self.limit = limit
        self.timeout_seconds = timeout_seconds

    def _get_key(self, identifier: str, operation_type: str) -> str:
        return f"concurrency:{operation_type}:{identifier}"

    def acquire(self, identifier: str, operation_type: str) -> str:
        """
        Increment the concurrency counter by adding an active task to a sorted set atomically.
        Raises ConcurrencyLimitError if the limit is exceeded.
        Returns a task_id to be used when releasing.
        """
        key = self._get_key(identifier, operation_type)
        task_id = str(uuid.uuid4())
        current_time = time.time()

        # Lua script to clean up expired entries, check limit, and add the new task atomically
        lua_script = """
        local key = KEYS[1]
        local current_time = tonumber(ARGV[1])
        local timeout = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local task_id = ARGV[4]

        -- Remove expired tasks
        redis.call('ZREMRANGEBYSCORE', key, '-inf', current_time - timeout)

        -- Check current count
        local current_count = redis.call('ZCARD', key)

        if current_count >= limit then
            return 0
        end

        -- Add the new task
        redis.call('ZADD', key, current_time, task_id)
        -- Set expiration on the key itself to prevent it staying in memory forever
        redis.call('EXPIRE', key, timeout * 2)

        return 1
        """

        # Execute Lua script atomically
        try:
            success = redis_client.eval(lua_script, 1, key, current_time, self.timeout_seconds, self.limit, task_id)
            try:
                success_int = int(success)
            except Exception:
                success_int = 1
        except Exception as e:
            # Check if redis connection error
            if "Connection" in type(e).__name__ or "Timeout" in type(e).__name__:
                return task_id
            raise

        if success_int == 0:
            raise ConcurrencyLimitError(
                message="Concurrency limit exceeded",
                details={
                    "limit": self.limit,
                    "operation_type": operation_type
                }
            )

        return task_id

    def release(self, identifier: str, operation_type: str, task_id: str) -> None:
        """
        Decrement the concurrency counter by removing the task from the sorted set.
        """
        key = self._get_key(identifier, operation_type)
        try:
            redis_client.zrem(key, task_id)
        except Exception:
            pass

    @contextlib.contextmanager
    def limit_concurrency(self, identifier: str, operation_type: str) -> Generator[str, None, None]:
        """
        Context manager to acquire and release a concurrency slot.
        Yields the task_id.
        """
        task_id = self.acquire(identifier, operation_type)
        try:
            yield task_id
        finally:
            self.release(identifier, operation_type, task_id)
