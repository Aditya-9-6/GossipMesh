import pytest
from gossipmesh.sync.vector_clock import VectorClock

def test_vector_clock_basic():
    vc1 = VectorClock({"nodeA": 1})
    vc2 = VectorClock({"nodeA": 2})
    assert vc1.compare(vc2) == "BEFORE"
    assert vc2.compare(vc1) == "AFTER"
    assert vc1.compare(VectorClock({"nodeA": 1})) == "EQUAL"

def test_vector_clock_concurrent():
    vc1 = VectorClock({"nodeA": 2, "nodeB": 1})
    vc2 = VectorClock({"nodeA": 1, "nodeB": 2})
    assert vc1.compare(vc2) == "CONCURRENT"

def test_vector_clock_compaction():
    vc = VectorClock({"n1": 1, "n2": 2, "n3": 3})
    vc.compact(max_entries=2)
    assert len(vc.clock) == 2
    assert "n3" in vc.clock
    assert "n2" in vc.clock
    assert "n1" not in vc.clock
