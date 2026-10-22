"""Comprehensive unit tests for Per-tenant Concurrency (Task 61)."""

import time
import pytest
from gossipmesh.core.exceptions import ConcurrencyLimitError
from gossipmesh.runtime.concurrency import (
    TenantConcurrencyLimiter,
    TenantConcurrencySlot,
    ConcurrencySlotType,
)


@pytest.fixture
def limiter():
    lim = TenantConcurrencyLimiter(stale_lease_seconds=300)
    lim.reset()
    return lim


def test_slot_acquisition_and_exhaustion(limiter):
    org_id = 1
    slot_type = ConcurrencySlotType.REVIEWS.value
    limit = limiter.get_limit(org_id, slot_type)
    assert limit == 3

    leases = []
    for _ in range(limit):
        lid = limiter.acquire(org_id, slot_type)
        assert lid is not None
        leases.append(lid)

    assert limiter.get_active_count(org_id, slot_type) == limit

    # Acquiring one more must raise ConcurrencyLimitError
    with pytest.raises(ConcurrencyLimitError) as exc:
        limiter.acquire(org_id, slot_type, timeout=0.0)
    assert "capacity (3/3) exhausted" in str(exc.value.message)

    # Release one lease
    limiter.release(org_id, slot_type, leases.pop(0))
    assert limiter.get_active_count(org_id, slot_type) == limit - 1

    # Now acquire should succeed
    new_lid = limiter.acquire(org_id, slot_type)
    assert new_lid is not None


def test_tenant_isolation(limiter):
    slot_type = ConcurrencySlotType.INDEXING.value

    # Exhaust Org 1 indexing slots (limit: 2)
    l1 = limiter.acquire(1, slot_type)
    l2 = limiter.acquire(1, slot_type)
    assert limiter.get_active_count(1, slot_type) == 2

    with pytest.raises(ConcurrencyLimitError):
        limiter.acquire(1, slot_type)

    # Org 2 must NOT be impacted by Org 1 exhaustion
    org2_l1 = limiter.acquire(2, slot_type)
    assert org2_l1 is not None
    assert limiter.get_active_count(2, slot_type) == 1


def test_all_concurrency_slot_types(limiter):
    org_id = 5
    for st in ConcurrencySlotType:
        lid = limiter.acquire(org_id, st.value)
        assert lid is not None
        limiter.release(org_id, st.value, lid)


def test_custom_limit_override(limiter):
    org_id = 10
    slot_type = ConcurrencySlotType.SANDBOX_JOBS.value

    assert limiter.get_limit(org_id, slot_type) == 2
    limiter.set_limit(org_id, slot_type, 5)
    assert limiter.get_limit(org_id, slot_type) == 5

    leases = []
    for _ in range(5):
        leases.append(limiter.acquire(org_id, slot_type))

    assert limiter.get_active_count(org_id, slot_type) == 5

    with pytest.raises(ConcurrencyLimitError):
        limiter.acquire(org_id, slot_type)


def test_context_manager_lifecycle_and_exception_safety(limiter):
    org_id = 20
    slot_type = ConcurrencySlotType.PROVIDER_CALLS.value

    assert limiter.get_active_count(org_id, slot_type) == 0

    with TenantConcurrencySlot(org_id, slot_type, limiter=limiter):
        assert limiter.get_active_count(org_id, slot_type) == 1

    assert limiter.get_active_count(org_id, slot_type) == 0

    # Verify release on error
    try:
        with TenantConcurrencySlot(org_id, slot_type, limiter=limiter):
            assert limiter.get_active_count(org_id, slot_type) == 1
            raise RuntimeError("Failure inside slot")
    except RuntimeError:
        pass

    assert limiter.get_active_count(org_id, slot_type) == 0


def test_stale_lease_reaping():
    fast_limiter = TenantConcurrencyLimiter(stale_lease_seconds=1)
    org_id = 30
    slot_type = ConcurrencySlotType.REVIEWS.value
    fast_limiter.set_limit(org_id, slot_type, 1)

    # Acquire the single available slot
    lid = fast_limiter.acquire(org_id, slot_type)
    assert fast_limiter.get_active_count(org_id, slot_type) == 1

    # Sleep past stale timeout
    time.sleep(1.1)

    # Next acquire should reap the stale lease and grant new lease
    new_lid = fast_limiter.acquire(org_id, slot_type)
    assert new_lid != lid
    assert fast_limiter.get_active_count(org_id, slot_type) == 1
