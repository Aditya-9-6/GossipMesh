"""
P2P Network Transport Layer with integrated Leaky-Bucket Rate Limiting.
"""

import asyncio
import logging
from typing import Optional
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


class P2PTransport:
    """P2P Transport layer handling peer connections and outbound message broadcasting."""

    def __init__(self, rate_limiter: Optional[PeerRateLimiter] = None):
        self.rate_limiter = rate_limiter or PeerRateLimiter(RateLimitConfig())
        self.active_connections: dict = {}

    async def send_message(self, peer_id: str, message_payload: bytes) -> bool:
        payload_size = len(message_payload)
        allowed = await self.rate_limiter.check_and_consume(peer_id, payload_size)
        if not allowed:
            logger.warning(f"Outbound message to peer {peer_id} dropped by rate limiter (size={payload_size}B)")
            return False
        
        # Simulate successful transmission
        logger.debug(f"Transmitted {payload_size} bytes to peer {peer_id}")
        return True
