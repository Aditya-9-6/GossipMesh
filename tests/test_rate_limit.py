import unittest
from unittest.mock import MagicMock, patch
from gossipmesh.core.rate_limit import RateLimiter
from gossipmesh.core.exceptions import RateLimitError


class TestRateLimiter(unittest.TestCase):
    @patch("gossipmesh.core.rate_limit.redis_client")
    def test_rate_limiter_allowed(self, mock_redis):
        pipe = MagicMock()
        pipe.execute.return_value = [1, 60000]
        mock_redis.pipeline.return_value = pipe

        limiter = RateLimiter(limit=10, window=60)
        is_allowed, remaining, reset_time = limiter.check_limit("user:1", "test")
        self.assertTrue(is_allowed)
        self.assertEqual(remaining, 9)

    @patch("gossipmesh.core.rate_limit.redis_client")
    def test_rate_limiter_exceeded(self, mock_redis):
        pipe = MagicMock()
        pipe.execute.return_value = [11, 50000]
        mock_redis.pipeline.return_value = pipe

        limiter = RateLimiter(limit=10, window=60)
        with self.assertRaises(RateLimitError):
            limiter.enforce("user:1", "test")
