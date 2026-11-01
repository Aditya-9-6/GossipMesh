import asyncio
import pytest

from gossipmesh.p2p.dedup import CompressedBloomFilterDedup as CountingBloomFilter


class BoundedLRUGossipRingBuffer:
    def __init__(self, max_capacity: int, bloom_capacity: int):
        pass


@pytest.mark.asyncio
async def test_counting_bloom_filter():
    bloom = CountingBloomFilter(capacity=100, error_rate=0.01)
    assert not bloom.check("msg_1")
    bloom.add("msg_1")
    assert bloom.check("msg_1")
    bloom.clear()
    assert not bloom.check("msg_1")


@pytest.mark.asyncio
async def test_bounded_lru_gossip_ring_buffer():
    pass
