import unittest
from unittest.mock import patch, MagicMock
from gossipmesh.core.concurrency_limit import ConcurrencyLimiter
from gossipmesh.core.exceptions import ConcurrencyLimitError
import time

class TestConcurrencyLimiter(unittest.TestCase):
    @patch("gossipmesh.core.concurrency_limit.redis_client")
    def test_acquire_release_success(self, mock_redis):
        # We simulate the fallback mechanism by making eval return 1 directly
        mock_redis.eval.return_value = 1
        mock_redis.zcard.return_value = 0

        limiter = ConcurrencyLimiter(limit=5)

        # Test context manager
        with limiter.limit_concurrency("org_1", "test_op") as task_id:
            # Mock asserts
            mock_redis.eval.assert_called_once()
            self.assertIsNotNone(task_id)

        mock_redis.zrem.assert_called_with("concurrency:test_op:org_1", task_id)

    @patch("gossipmesh.core.concurrency_limit.redis_client")
    def test_acquire_limit_exceeded(self, mock_redis):
        # Setup mock behavior: limit is 2, current count is 2 (so eval returns 0)
        mock_redis.eval.return_value = 0
        mock_redis.zcard.return_value = 2

        limiter = ConcurrencyLimiter(limit=2)

        with self.assertRaises(ConcurrencyLimitError):
            limiter.acquire("org_1", "test_op")

        mock_redis.zadd.assert_not_called()

if __name__ == "__main__":
    unittest.main()
