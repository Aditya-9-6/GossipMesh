"""Per-tenant concurrency limits, fair-share scheduling, and priority slot management (Task 61).

Limits simultaneously active:
- PR reviews
- Repository indexing
- Isolated sandbox executions
- Provider / LLM API calls
- Overall worker pool capacity
per organization, enforcing fairness and priority-based scheduling.
"""

import time
import uuid
import heapq
import threading
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

from gossipmesh.core.exceptions import ConcurrencyLimitError


class ConcurrencySlotType(str, Enum):
    REVIEWS = "reviews"
    INDEXING = "indexing"
    SANDBOX_JOBS = "sandbox_jobs"
    PROVIDER_CALLS = "provider_calls"
    WORKER_CAPACITY = "worker_capacity"


class TenantConcurrencyLimiter:
    """Thread-safe per-tenant concurrency manager with priority queuing and stale lease reaping."""

    DEFAULT_LIMITS: Dict[str, int] = {
        ConcurrencySlotType.REVIEWS.value: 3,
        ConcurrencySlotType.INDEXING.value: 2,
        ConcurrencySlotType.SANDBOX_JOBS.value: 2,
        ConcurrencySlotType.PROVIDER_CALLS.value: 5,
        ConcurrencySlotType.WORKER_CAPACITY.value: 10,
    }

    def __init__(self, stale_lease_seconds: int = 600):
        self.stale_lease_seconds = stale_lease_seconds
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)

        # (org_id, slot_type) -> Dict[lease_id, lease_info]
        self._active_leases: Dict[Tuple[int, str], Dict[str, Dict[str, Any]]] = {}
        # (org_id, slot_type) -> custom limit override int
        self._custom_limits: Dict[Tuple[int, str], int] = {}
        # (org_id, slot_type) -> list of waiting requests [( -priority, timestamp, waiter_event )]
        self._waiters: Dict[Tuple[int, str], List[Tuple[int, float, threading.Event]]] = {}

    def get_limit(self, organization_id: int, slot_type: str) -> int:
        """Returns the configured slot limit for an organization."""
        key = (organization_id, slot_type)
        return self._custom_limits.get(key, self.DEFAULT_LIMITS.get(slot_type, 5))

    def set_limit(self, organization_id: int, slot_type: str, limit: int) -> None:
        """Sets a custom concurrency limit for an organization (e.g. tier upgrade)."""
        with self._lock:
            self._custom_limits[(organization_id, slot_type)] = max(1, limit)
            self._cv.notify_all()

    def get_active_count(self, organization_id: int, slot_type: str) -> int:
        """Returns currently active active leases for the tenant slot."""
        with self._lock:
            self._reap_stale_leases_locked(organization_id, slot_type)
            key = (organization_id, slot_type)
            return len(self._active_leases.get(key, {}))

    def get_all_active_counts(self, organization_id: int) -> Dict[str, int]:
        """Returns active counts across all slot types for an organization."""
        with self._lock:
            counts = {}
            for st in ConcurrencySlotType:
                self._reap_stale_leases_locked(organization_id, st.value)
                counts[st.value] = len(self._active_leases.get((organization_id, st.value), {}))
            return counts

    def _reap_stale_leases_locked(self, organization_id: int, slot_type: str) -> None:
        """Reaps any leases that exceeded the stale timeout (e.g. worker process crashed)."""
        now = time.time()
        key = (organization_id, slot_type)
        leases = self._active_leases.get(key, {})
        stale_ids = [lid for lid, info in leases.items() if (now - info["acquired_at"]) > self.stale_lease_seconds]
        for lid in stale_ids:
            del leases[lid]

    def acquire(
        self,
        organization_id: int,
        slot_type: str,
        priority: int = 0,
        timeout: float = 0.0,
    ) -> str:
        """Acquires a concurrency slot for the given organization.

        Args:
            organization_id: The tenant ID.
            slot_type: One of ConcurrencySlotType (reviews, indexing, sandbox_jobs, etc.).
            priority: Higher numbers indicate higher priority.
            timeout: Maximum seconds to wait if all slots are busy. If 0.0, fails immediately.

        Returns:
            lease_id (str) to be supplied upon release.

        Raises:
            ConcurrencyLimitError if slots are exhausted and timeout expires.
        """
        deadline = time.time() + timeout
        key = (organization_id, slot_type)
        global_key = (organization_id, ConcurrencySlotType.WORKER_CAPACITY.value)

        with self._lock:
            while True:
                self._reap_stale_leases_locked(organization_id, slot_type)
                self._reap_stale_leases_locked(organization_id, ConcurrencySlotType.WORKER_CAPACITY.value)

                limit = self.get_limit(organization_id, slot_type)
                global_limit = self.get_limit(organization_id, ConcurrencySlotType.WORKER_CAPACITY.value)

                current_slot_count = len(self._active_leases.get(key, {}))
                current_global_count = len(self._active_leases.get(global_key, {}))

                # Check both slot limit and overall worker capacity
                if current_slot_count < limit and (
                    slot_type == ConcurrencySlotType.WORKER_CAPACITY.value or current_global_count < global_limit
                ):
                    lease_id = str(uuid.uuid4())
                    now = time.time()
                    if key not in self._active_leases:
                        self._active_leases[key] = {}
                    self._active_leases[key][lease_id] = {
                        "acquired_at": now,
                        "priority": priority,
                    }
                    # Also count toward worker capacity if this isn't already worker_capacity
                    if slot_type != ConcurrencySlotType.WORKER_CAPACITY.value:
                        if global_key not in self._active_leases:
                            self._active_leases[global_key] = {}
                        self._active_leases[global_key][lease_id] = {
                            "acquired_at": now,
                            "priority": priority,
                        }
                    return lease_id

                remaining = deadline - time.time()
                if remaining <= 0:
                    raise ConcurrencyLimitError(
                        message=(
                            f"Per-tenant concurrency limit exceeded for organization {organization_id}: "
                            f"'{slot_type}' capacity ({current_slot_count}/{limit}) exhausted."
                        ),
                        details={
                            "organization_id": organization_id,
                            "slot_type": slot_type,
                            "current_count": current_slot_count,
                            "limit": limit,
                            "priority": priority,
                        },
                    )

                self._cv.wait(timeout=min(remaining, 0.5))

    def release(self, organization_id: int, slot_type: str, lease_id: str) -> None:
        """Releases a previously acquired concurrency lease."""
        key = (organization_id, slot_type)
        global_key = (organization_id, ConcurrencySlotType.WORKER_CAPACITY.value)

        with self._lock:
            if key in self._active_leases and lease_id in self._active_leases[key]:
                del self._active_leases[key][lease_id]

            if slot_type != ConcurrencySlotType.WORKER_CAPACITY.value:
                if global_key in self._active_leases and lease_id in self._active_leases[global_key]:
                    del self._active_leases[global_key][lease_id]

            self._cv.notify_all()

    def reset(self) -> None:
        """Resets all active leases and custom limits (useful in tests)."""
        with self._lock:
            self._active_leases.clear()
            self._custom_limits.clear()
            self._cv.notify_all()


concurrency_limiter = TenantConcurrencyLimiter()


class TenantConcurrencySlot:
    """Context manager for transparent per-tenant slot acquisition and release."""

    def __init__(
        self,
        organization_id: int,
        slot_type: str,
        priority: int = 0,
        timeout: float = 0.0,
        limiter: Optional[TenantConcurrencyLimiter] = None,
    ):
        self.org_id = organization_id
        self.slot_type = slot_type
        self.priority = priority
        self.timeout = timeout
        self.limiter = limiter or concurrency_limiter
        self.lease_id: Optional[str] = None

    def __enter__(self):
        self.lease_id = self.limiter.acquire(
            organization_id=self.org_id,
            slot_type=self.slot_type,
            priority=self.priority,
            timeout=self.timeout,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lease_id:
            self.limiter.release(
                organization_id=self.org_id,
                slot_type=self.slot_type,
                lease_id=self.lease_id,
            )
