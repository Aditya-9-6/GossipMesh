import asyncio
import logging
from typing import Optional, Callable
from gossipmesh.p2p.ratelimit import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

class P2PTransport:
    """High-throughput P2P transport layer with integrated rate-limiting protection."""

    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0):
        self.limiter = TokenBucketRateLimiter(capacity=capacity, refill_rate=refill_rate)
        self.dropped_messages = 0
        self.accepted_messages = 0

    def handle_message(self, peer_id: str, payload_size: float = 1.0) -> bool:
        """Evaluate incoming gossip payload against rate limits."""
        if not self.limiter.allow(peer_id, cost=payload_size):
            self.dropped_messages += 1
            logger.warning(f"Rate limit exceeded for peer {peer_id}. Payload dropped.")
            return False
        self.accepted_messages += 1
        return True
