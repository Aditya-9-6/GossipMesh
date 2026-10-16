import unittest
import time
from unittest.mock import patch, MagicMock
from gossipmesh.core.rate_limit import RateLimiter
from gossipmesh.core.exceptions import RateLimitError

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        # We need to stop the global patcher in tests/__init__.py for this specific test
        import tests
        try:
            tests.patcher.stop()
        except:
            pass

    def tearDown(self):
        import tests
        try:
            mock = tests.patcher.start()
            mock.return_value = (True, 99, int(time.time() + 60))
        except:
            pass

    @patch("gossipmesh.core.rate_limit.redis_client")
    def test_rate_limiter_allows_request(self, mock_redis):
        # Setup mock
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        # Return [current_count, ttl]
        mock_pipe.execute.return_value = [1, 60000]

        limiter = RateLimiter(limit=5, window=60)
        is_allowed, remaining, reset_time = limiter.check_limit("test_id", "test_type")

        self.assertTrue(is_allowed)
        self.assertEqual(remaining, 4)
        mock_pipe.incr.assert_called_once_with("ratelimit:test_type:test_id")
        mock_pipe.pttl.assert_called_once_with("ratelimit:test_type:test_id")

    @patch("gossipmesh.core.rate_limit.redis_client")
    def test_rate_limiter_blocks_request(self, mock_redis):
        # Setup mock
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        # Return [current_count, ttl]
        mock_pipe.execute.return_value = [6, 30000]

        limiter = RateLimiter(limit=5, window=60)
        is_allowed, remaining, reset_time = limiter.check_limit("test_id", "test_type")

        self.assertFalse(is_allowed)
        self.assertEqual(remaining, 0)

        with self.assertRaises(RateLimitError):
            limiter.enforce("test_id", "test_type")

    @patch("gossipmesh.core.rate_limit.redis_client")
    def test_rate_limiter_redis_failure(self, mock_redis):
        # Setup mock to raise Exception
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        mock_pipe.execute.side_effect = Exception("Connection refused")

        limiter = RateLimiter(limit=5, window=60)
        is_allowed, remaining, reset_time = limiter.check_limit("test_id", "test_type")

        # Should fail open
        self.assertTrue(is_allowed)
        self.assertEqual(remaining, 5)

if __name__ == "__main__":
    unittest.main()
