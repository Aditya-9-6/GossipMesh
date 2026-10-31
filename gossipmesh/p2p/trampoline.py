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
        """Thread-safely gets the current connection state of a peer."""
        async with self._lock:
            return self._states.get(peer_id, ConnectionState.IDLE)

    async def set_state(self, peer_id: str, state: ConnectionState) -> None:
        """Thread-safely sets the connection state of a peer."""
        async with self._lock:
            self._states[peer_id] = state

    async def can_dial(self, peer_id: str) -> bool:
        """Checks if a peer is eligible for a dial attempt based on backoff schedule."""
        async with self._lock:
            state = self._states.get(peer_id, ConnectionState.IDLE)
            if state == ConnectionState.CONNECTED:
                return False
            if state == ConnectionState.CONNECTING:
                return False

            next_time = self._next_attempt_time.get(peer_id, 0.0)
            if time.time() < next_time:
                return False

            attempts = self._attempts.get(peer_id, 0)
            if attempts >= self.max_retries:
                return False

            return True

    def calculate_backoff(self, attempt: int) -> float:
        """Calculates exponential backoff with randomized jitter."""
        backoff = self.base_backoff * (self.backoff_multiplier ** max(0, attempt - 1))
        backoff = min(backoff, self.max_backoff)
        jitter = backoff * self.jitter_factor * (random.random() * 2.0 - 1.0)
        return max(0.01, backoff + jitter)

    async def record_failure(self, peer_id: str) -> Tuple[ConnectionState, float]:
        """Records a connection failure, computes backoff, and updates state atomically."""
        async with self._lock:
            attempts = self._attempts.get(peer_id, 0) + 1
            self._attempts[peer_id] = attempts

            if attempts >= self.max_retries:
                self._states[peer_id] = ConnectionState.FAILED
                return ConnectionState.FAILED, 0.0

            delay = self.calculate_backoff(attempts)
            self._next_attempt_time[peer_id] = time.time() + delay
            self._states[peer_id] = ConnectionState.BACKOFF
            return ConnectionState.BACKOFF, delay

    async def record_success(self, peer_id: str) -> None:
        """Records a successful connection, resetting attempts and backoff counters."""
        async with self._lock:
            self._states[peer_id] = ConnectionState.CONNECTED
            self._attempts[peer_id] = 0
            self._next_attempt_time.pop(peer_id, None)

    async def reset(self, peer_id: str) -> None:
        """Resets all tracking states for a given peer."""
        async with self._lock:
            self._states.pop(peer_id, None)
            self._attempts.pop(peer_id, None)
            self._next_attempt_time.pop(peer_id, None)

    async def dial_with_trampoline(
        self,
        peer_id: str,
        dial_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """
        Executes an asynchronous dial attempt through the trampoline, managing
        state transitions, concurrency locks, and exponential backoff on failure.
        """
        if not await self.can_dial(peer_id):
            return False

        async with self._lock:
            self._states[peer_id] = ConnectionState.CONNECT
            self._states[peer_id] = ConnectionState.CONNECTING

        try:
            success = await dial_func(peer_id, *args, **kwargs)
            if success:
                await self.record_success(peer_id)
                return True
            else:
                await self.record_failure(peer_id)
                return False
        except Exception as e:
            logger.debug(f"Trampoline dial exception for peer {peer_id}: {e}")
            await self.record_failure(peer_id)
            return False
