import asyncio
import pytest

from gossipmesh.p2p.dedup import CompressedBloomFilterDedup


@pytest.mark.asyncio
async def test_compressed_bloom_filter_dedup():
    bloom = CompressedBloomFilterDedup(capacity=100, error_rate=0.01)

    assert not bloom.check("msg_1")
    assert bloom.add("msg_1") is False
    assert bloom.check("msg_1") is True
    assert bloom.add("msg_1") is True

    bloom.clear()
    assert bloom.check("msg_1") is False
