import os
from unittest.mock import patch, MagicMock
import time

# Set up required environment variables before any tests run
os.environ["ENCRYPTION_KEY"] = "b_wH5yL7g3XQz8T1kVcZp6sN0mR9dE2fA4uYxWqVjMw="
os.environ["SECRET_KEY"] = "supersecretkey_please_change_in_production"
os.environ["POSTGRES_USER"] = "testuser"
os.environ["POSTGRES_PASSWORD"] = "testpass"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "testdb"

# Globally mock rate limiter for unittest discovery
patcher = patch("gossipmesh.core.rate_limit.RateLimiter.check_limit")
mock_check = patcher.start()
mock_check.return_value = (True, 99, int(time.time() + 60))
