import asyncio
import logging
from typing import Optional, Callable, Awaitable
from gossipmesh.p2p.dedup import CompressedBloomFilterDedup
from gossipmesh.p2p.fragmentation import FragmentationManager, PacketFragment

logger = logging.getLogger(__name__)


class P2PTransport:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, rate_limit_rps: float = 100.0):
        self.host = host
        self.port = port
        self.rate_limit_rps = rate_limit_rps
        self.dedup = CompressedBloomFilterDedup()
        self.fragmentation = FragmentationManager()
        self._running = False
        self._tokens = rate_limit_rps
        self._last_refill = asyncio.get_event_loop().time() if asyncio._get_running_loop() else 0.0

    async def start(self) -> None:
        self._running = True
        logger.info(f"P2PTransport started on {self.host}:{self.port}")

    async def stop(self) -> None:
        self._running = False
        logger.info("P2PTransport stopped")

    def _check_rate_limit(self) -> bool:
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self.rate_limit_rps, self._tokens + elapsed * self.rate_limit_rps)
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False

    async def send_gossip(self, peer_addr: str, message_id: str, payload: bytes) -> bool:
        if not self._check_rate_limit():
            logger.warning(f"Rate limit exceeded for outbound message to {peer_addr}")
            return False
        if message_id in self.dedup:
            return True
        self.dedup.add(message_id)
        logger.debug(f"Sending gossip message {message_id} to {peer_addr} (size: {len(payload)} bytes)")
        return True
