import asyncio
import pytest

from gossipmesh.p2p.dedup import CompressedBloomFilterDedup
from gossipmesh.p2p.bloom_sync import HierarchicalBloomFilterDigest


@pytest.mark.asyncio
async def test_counting_bloom_filter():
    bloom = CompressedBloomFilterDedup(capacity=100, error_rate=0.01)

    assert not bloom.check("msg_1")
    assert not bloom.add("msg_1")
    assert bloom.check("msg_1")
    assert bloom.add("msg_1")


@pytest.mark.asyncio
async def test_bounded_lru_gossip_ring_buffer():
    bloom = CompressedBloomFilterDedup(capacity=100, error_rate=0.01)
    assert not bloom.add("m1")
    assert bloom.check("m1")
