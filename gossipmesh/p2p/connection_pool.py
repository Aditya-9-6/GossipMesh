import enum
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from gossipmesh.p2p.backpressure import BackpressureSignalManager, BackpressureConfig, BackpressureState


class ConnectionPriority(enum.IntEnum):
    """Connection priority levels (lower integer = higher priority)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(frozen=True)
class ConnectionPoolConfig:
    """Configuration parameters for the leaky-bucket connection pool."""

    max_capacity: int = 100
    leak_rate: float = 5.0  # Connections drained per second in leaky-bucket mode
    default_priority: ConnectionPriority = ConnectionPriority.NORMAL
    backpressure_config: Optional[BackpressureConfig] = None


@dataclass
class PeerConnection:
    """Represents an active peer connection inside the pool with metadata."""

    peer_id: str
    socket_ref: Any
    priority: ConnectionPriority
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    bytes_transferred: int = 0


class LeakyBucketConnectionPool:
    """Deterministic leaky-bucket connection pool manager regulating inbound and
    outbound peer socket allocations with LRU eviction and backpressure signaling."""

    def __init__(self, config: Optional[ConnectionPoolConfig] = None) -> None:
        self.config = config or ConnectionPoolConfig()
        self._lock = threading.Lock()
        self._connections: Dict[str, PeerConnection] = {}
        self._lru_order: List[str] = []
        self._backpressure = BackpressureSignalManager(self.config.backpressure_config)
        self._dropped_count: int = 0
        self._allocated_count: int = 0

    def acquire(self, peer_id: str, socket_ref: Any, priority: Optional[ConnectionPriority] = None) -> bool:
        """Acquires a socket allocation in the connection pool.
        Enforces strict capacity bounds using LRU eviction and backpressure signaling.
        Returns True if successfully added, False if dropped due to high-priority backpressure shedding."""
        prio = priority if priority is not None else self.config.default_priority
        now = time.time()

        with self._lock:
            # If peer already exists, update touch time and priority
            if peer_id in self._connections:
                conn = self._connections[peer_id]
                conn.last_accessed = now
                conn.priority = prio
                conn.socket_ref = socket_ref
                if peer_id in self._lru_order:
                    self._lru_order.remove(peer_id)
                self._lru_order.append(peer_id)
                return True

            # Check backpressure before accepting new connection
            current_count = len(self._connections)
            bp_state = self._backpressure.update_saturation(current_count, self.config.max_capacity)

            # If at or over capacity, we need to evict or shed
            if current_count >= self.config.max_capacity:
                # If we are in critical backpressure and incoming is low/normal, consider dropping
                if self._backpressure.should_drop_low_priority() and prio >= ConnectionPriority.NORMAL:
                    if prio == ConnectionPriority.LOW:
                        self._dropped_count += 1
                        return False

                # Evict LRU connection to make room
                if self._lru_order:
                    evict_id = self._lru_order.pop(0)
                    if evict_id in self._connections:
                        del self._connections[evict_id]
                else:
                    self._dropped_count += 1
                    return False

            # Add new connection
            new_conn = PeerConnection(
                peer_id=peer_id,
                socket_ref=socket_ref,
                priority=prio,
                created_at=now,
                last_accessed=now,
            )
            self._connections[peer_id] = new_conn
            if peer_id in self._lru_order:
                self._lru_order.remove(peer_id)
            self._lru_order.append(peer_id)
            self._allocated_count += 1

            # Update saturation post-allocation
            self._backpressure.update_saturation(len(self._connections), self.config.max_capacity)
            return True

    def release(self, peer_id: str) -> bool:
        """Releases a peer connection from the pool."""
        with self._lock:
            if peer_id in self._connections:
                del self._connections[peer_id]
                if peer_id in self._lru_order:
                    self._lru_order.remove(peer_id)
                self._backpressure.update_saturation(len(self._connections), self.config.max_capacity)
                return True
            return False

    def touch(self, peer_id: str) -> bool:
        """Refreshes LRU recency for active peer connection."""
        with self._lock:
            if peer_id in self._connections:
                self._connections[peer_id].last_accessed = time.time()
                if peer_id in self._lru_order:
                    self._lru_order.remove(peer_id)
                self._lru_order.append(peer_id)
                return True
            return False

    def get(self, peer_id: str) -> Optional[PeerConnection]:
        """Retrieves peer connection details."""
        with self._lock:
            return self._connections.get(peer_id)

    def size(self) -> int:
        """Returns active connection count."""
        with self._lock:
            return len(self._connections)

    def leak(self, count: int = 1) -> List[str]:
        """Leaky-bucket drop simulation: evicts up to `count` oldest LRU connections
        to simulate rate-limiting or resource draining under overload."""
        evicted = []
        with self._lock:
            for _ in range(count):
                if not self._lru_order:
                    break
                evict_id = self._lru_order.pop(0)
                if evict_id in self._connections:
                    del self._connections[evict_id]
                    evicted.append(evict_id)
            self._backpressure.update_saturation(len(self._connections), self.config.max_capacity)
        return evicted

    def get_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive connection pool telemetry."""
        with self._lock:
            bp_metrics = self._backpressure.get_metrics()
            return {
                "active_connections": len(self._connections),
                "max_capacity": self.config.max_capacity,
                "allocated_total": self._allocated_count,
                "dropped_total": self._dropped_count,
                "lru_queue_size": len(self._lru_order),
                "backpressure": bp_metrics,
            }

    def clear(self) -> None:
        """Clears all connections and resets pool state."""
        with self._lock:
            self._connections.clear()
            self._lru_order.clear()
            self._backpressure.reset()
            self._dropped_count = 0
            self._allocated_count = 0
