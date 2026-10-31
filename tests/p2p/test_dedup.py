import asyncio
import pytest

from gossipmesh.p2p.dedup import CountingBloomFilter, BoundedLRUGossipRingBuffer


@pytest.mark.asyncio
async def test_counting_bloom_filter():
    bloom = CountingBloomFilter(capacity=100, error_rate=0.01)
    
    assert not ("msg_1" in bloom)
    await bloom.add("msg_1")
    assert "msg_1" in bloom
    
    await bloom.remove("msg_1")
    # Due to possible false positives or collisions with small sizes, check behavior after removal
    # but with counting bloom filter, zeroing out hashes guarantees absence.
    assert not ("msg_1" in bloom)


@pytest.mark.asyncio
async def test_bounded_lru_gossip_ring_buffer():
    buf = BoundedLRUGossipRingBuffer(max_capacity=3, bloom_capacity=100)

    # Test additions
    evicted = await buf.add("m1", {"data": 1})
    assert evicted is None
    assert await buf.contains("m1") is True
    assert len(buf) == 1

    await buf.add("m2", {"data": 2})
    await buf.add("m3", {"data": 3})
    assert len(buf) == 3

    # Test LRU eviction when adding 4th item
    evicted = await buf.add("m4", {"data": 4})
    assert evicted == {"data": 1}
    assert await buf.contains("m1") is False
    assert await buf.contains("m4") is True
    assert len(buf) == 3

    # Test LRU update order via get/re-add
    # Current order: m2, m3, m4. Access m2 to make it most recent.
    val = await buf.get("m2")
    assert val == {
        "data": 2
    }

    # Adding m5 should now evict m3 instead of m2
    evicted = await buf.add("m5", {"data": 5})
    assert evicted == {"data": 3}
    assert await buf.contains("m3") is False
    assert await buf.contains("m2") is True
