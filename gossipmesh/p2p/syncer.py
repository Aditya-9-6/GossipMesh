import asyncio
import logging
from typing import Dict, Set, Optional, Any
from gossipmesh.p2p.protocol import GossipProtocol
from gossipmesh.p2p.entropy import VectorClockEntropy

logger = logging.getLogger(__name__)


class PeerSyncer:
    """Manages anti-entropy synchronization across mesh peers."""

    def __init__(self, protocol: GossipProtocol, interval: float = 30.0) -> None:
        self._protocol = protocol
        self._interval = interval
        self._entropy = VectorClockEntropy()
        self._task: Optional[asyncio.Task[Any]] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("PeerSyncer started with interval %.1fs", self._interval)

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PeerSyncer stopped")

    async def _sync_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                await self.synchronize_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in peer sync loop: %s", e)

    async def synchronize_once(self) -> Dict[str, Any]:
        """Performs a single anti-entropy sync round across connected peers."""
        peers = self._protocol.get_active_peers()
        sync_results = {}
        for peer_id in peers:
            try:
                remote_clock = await self._protocol.fetch_peer_clock(peer_id)
                local_clock = self._protocol.get_local_clock()
                if self._entropy.needs_sync(local_clock, remote_clock):
                    diff = self._entropy.compute_diff(local_clock, remote_clock)
                    await self._protocol.reconcile(peer_id, diff)
                    sync_results[peer_id] = "reconciled"
                else:
                    sync_results[peer_id] = "up_to_date"
            except Exception as e:
                logger.warning("Failed to sync with peer %s: %s", peer_id, e)
                sync_results[peer_id] = f"error: {e}"
        return sync_results
