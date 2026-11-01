import pytest
from gossipmesh.p2p.bloom_sync import HierarchicalBloomFilterDigest

def test_hierarchical_bloom_filter_initialization():
    hbf = HierarchicalBloomFilterDigest(capacity=1000, error_rate=0.01, levels=3)
    assert hbf.tier_count == 3
    assert hbf.capacity == 1000
    assert hbf.error_rate == 0.01

def test_hierarchical_bloom_filter_add_and_contains():
    hbf = HierarchicalBloomFilterDigest(capacity=500, error_rate=0.05, levels=2)
    item = "agent-node-alpha-state-update"
    assert item not in hbf
    hbf.add(item)
    assert item in hbf

def test_hierarchical_bloom_filter_comparison():
    hbf1 = HierarchicalBloomFilterDigest(capacity=1000, error_rate=0.01, levels=3)
    hbf2 = HierarchicalBloomFilterDigest(capacity=1000, error_rate=0.01, levels=3)
    
    item = "consensus-vector-v1"
    hbf1.add(item)
    
    mismatches = hbf1.compare_digest(hbf2)
    assert len(mismatches) > 0

    hbf2.add(item)
    mismatches_resolved = hbf1.compare_digest(hbf2)
    assert len(mismatches_resolved) == 0

def test_hierarchical_bloom_filter_serialization():
    hbf = HierarchicalBloomFilterDigest(capacity=500, error_rate=0.02, levels=2)
    hbf.add(
        "shard-reconciliation-key"
    )
    
    data = hbf.serialize()
    restored = HierarchicalBloomFilterDigest.deserialize(data)
    
    assert "shard-reconciliation-key" in restored
    assert restored.tier_count == hbf.tier_count
    assert restored.capacity == hbf.capacity
