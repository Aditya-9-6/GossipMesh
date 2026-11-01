"""Unit tests for CompressedBloomFilterDedup and GossipTransport deduplication.
"""

import pytest
from gossipmesh.p2p.dedup import CompressedBloomFilterDedup
from gossipmesh.p2p.transport import GossipTransport


def test_bloom_filter_basic_dedup():
    bloom = CompressedBloomFilterDedup(capacity=1000, error_rate=0.01)
    msg_id = "msg-12345"

    # First time add should return False (not a duplicate yet)
    assert bloom.add(msg_id) is False
    # Second time add should return True (already present)
    assert bloom.add(msg_id) is True
    assert bloom.check(msg_id) is True


def test_bloom_filter_memory_footprint():
    bloom = CompressedBloomFilterDedup(capacity=10000, error_rate=0.01)
    # Must consume less than 64KB (65536 bytes)
    assert bloom.memory_usage_bytes() <= 65536


def test_bloom_filter_clear():
    bloom = CompressedBloomFilterDedup(capacity=500, error_rate=0.01)
    msg_id = "msg-clear-test"
    bloom.add(msg_id)
    assert bloom.check(msg_id) is True

    bloom.clear()
    assert bloom.check(msg_id) is False


def test_gossip_transport_integration():
    transport = GossipTransport(node_id="node-alpha")
    msg_id = "gossip-payload-999"

    assert transport.receive_message(msg_id, {"data": "hello"}) is True
    assert transport.receive_message(msg_id, {"data": "hello"}) is False
