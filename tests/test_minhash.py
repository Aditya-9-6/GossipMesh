from __future__ import annotations

import pytest
import array
from gossipmesh.p2p.minhash import MinHashSketch


def test_minhash_initialization():
    sketch = MinHashSketch(num_perm=64, seed=123)
    assert sketch.num_perm == 64
    assert sketch.seed == 123
    assert len(sketch.memory_view) == 64


def test_minhash_update_and_jaccard_identical():
    s1 = MinHashSketch(num_perm=128)
    s2 = MinHashSketch(num_perm=128)

    tokens = ["agent_alpha", "node_beta", "consensus_round_1"]
    s1.update_batch(tokens)
    s2.update_batch(tokens)

    sim = s1.jaccard(s2)
    assert sim == 1.0


def test_minhash_jaccard_disjoint():
    s1 = MinHashSketch(num_perm=128, seed=42)
    s2 = MinHashSketch(num_perm=128, seed=42)

    s1.update_batch(["apple", "banana", "cherry"])
    s2.update_batch(["dog", "elephant", "fox"])

    sim = s1.jaccard(s2)
    assert 0.0 <= sim <= 0.2


def test_minhash_downsample():
    s1 = MinHashSketch(num_perm=128)
    s1.update("test_token")
    ds = s1.downsample(32)
    assert ds.num_perm == 32
    assert len(ds.memory_view) == 32


def test_minhash_dimension_mismatch():
    s1 = MinHashSketch(num_perm=64)
    s2 = MinHashSketch(num_perm=128)
    with pytest.raises(ValueError):
        s1.jaccard(s2)
