import asyncio
import logging
import random
import time
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    IDLE = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    BACKOFF = auto()
    FAILED = auto()


class PeerConnectionTrampoline:
    """
    High-throughput, non-blocking connection trampoline managing outbound peer
    dial attempts using exponential backoff with jitter and atomic state tracking.
    """

    def __init__(
        self,
        base_backoff: float = 0.5,
        max_backoff: float = 30.0,
        backoff_multiplier: float = 2.0,
        jitter_factor: float = 0.2,
        max_retries: int = 5,
    ):
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        self.jitter_factor = jitter_factor
        self.max_retries = max_retries

        self._states: Dict[str, ConnectionState] = {}
        self._attempts: Dict[str, int] = {}
        self._next_attempt_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get_state(self, peer_id: str) -> ConnectionState:
        async with self._lock:
            return self._states.get(peer_id, ConnectionState.IDLE)

    async def set_state(self, peer_id: str, state: ConnectionState) -> None:
        async with self._lock:
            self._states[peer_id] = state

    async def can_dial(self, peer_id: str) -> bool:
        async with self._lock:
            state = self._states.get(peer_id, ConnectionState.IDLE)
            if state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
                return False
            if state == ConnectionState.BACKOFF:
                next_time = self._next_attempt_time.get(peer_id, 0.0)
                if time.time() < next_time:
                    return False
            return True

    async def dial_with_trampoline(self, peer_id: str, dial_func: Callable[[], Any]) -> bool:
        async with self._lock:
            if not await self.can_dial(peer_id):
                return False
            self._states[peer_id] = ConnectionState.CONNECTING
            attempts = self._attempts.get(peer_id, 0)

        try:
            success = await dial_func()
            async with self._lock:
                if success:
                    self._states[peer_id] = ConnectionState.CONNECTED
                    self._attempts[peer_id] = 0
                    self._next_attempt_time.pop(peer_id, None)
                    return True
                else:
                    raise ConnectionError("Dial returned False")
        except Exception as e:
            async with self._lock:
                attempts += 1
                self._attempts[peer_id] = attempts
                if attempts >= self.max_retries:
                    self._states[peer_id] = ConnectionState.FAILED
                    logger.error(f"Max retries reached for peer {peer_id}: {e}")
                    return False
                else:
                    self._states[peer_id] = ConnectionState.BACKOFF
                    backoff = min(self.max_backoff, self.base_backoff * (self.backoff_multiplier ** (attempts - 1)))
                    jitter = backoff * self.jitter_factor * random.uniform(-1, 1)
                    self._next_attempt_time[peer_id] = time.time() + max(0.0, backoff + jitter)
                    return False

    async def reset(self, peer_id: str) -> None:
        async with self._lock:
            self._states.pop(peer_id, None)
            self._attempts.pop(peer_id, None)
            self._next_attempt_time.pop(peer_id, None)
