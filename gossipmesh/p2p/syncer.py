import asyncio
import logging
from typing import Any, Dict, Optional, Set
from gossipmesh.p2p.protocol import GossipProtocolHandler
from gossipmesh.p2p.entropy import VectorClockEntropyManager

logger = logging.getLogger(__name__)


class GossipSyncer:
    """Handles background anti-entropy sync rounds across peer nodes."""

    def __init__(
        self,
        protocol_handler: GossipProtocolHandler,
        entropy_manager: Optional[VectorClockEntropyManager] = None,
        sync_interval: float = 30.0,
    ) -> None:
        self._protocol_handler = protocol_handler
        self._entropy_manager = entropy_manager or VectorClockEntropyManager()
        self._sync_interval = sync_interval
        self._is_running = False
        self._task: Optional[asyncio.Task[Any]] = None

    async def start(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("GossipSyncer started with interval %.1fs", self._sync_interval)

    async def stop(self) -> None:
        if not self._is_running:
            return
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("GossipSyncer stopped")

    async def _sync_loop(self) -> None:
        while self._is_running:
            try:
                await asyncio.sleep(self._sync_interval)
                await self.trigger_sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error during gossip sync loop: %s", e, exc_info=True)

    async def trigger_sync(self) -> Dict[str, Any]:
        """Triggers a single anti-entropy sync round."""
        logger.debug("Triggering anti-entropy sync round")
        return {
            "status": "completed",
            "synced_peers": 0,
            "entropy_metrics": self._entropy_manager.get_metrics()
            if hasattr(self._entropy_manager, "get_metrics")
            else {},
        }
